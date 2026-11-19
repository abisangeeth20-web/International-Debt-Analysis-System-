-- ==================================================================
-- INTERNATIONAL DEBT ANALYSIS SYSTEM - MySQL database schema
-- Database: international_debt    Engine: InnoDB (foreign keys)
-- ==================================================================
-- Star schema, normalised so names are stored once:
--
--   countries (dimension) ----+
--                             +--< debt_data (fact: one row per country x indicator)
--   indicators (dimension) ---+
--   countries ---------------1:1-- country_macro (GNI, exports, imports, reserves)
--
-- Load it with:  python run_pipeline.py --mysql
-- (the pipeline runs this file, then inserts the cleaned rows)
-- ==================================================================

CREATE DATABASE IF NOT EXISTS international_debt
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE international_debt;

DROP VIEW IF EXISTS vw_top10_countries;
DROP VIEW IF EXISTS vw_country_debt_profile;
DROP TABLE IF EXISTS debt_data;       -- child tables first (FK order)
DROP TABLE IF EXISTS country_macro;
DROP TABLE IF EXISTS countries;
DROP TABLE IF EXISTS indicators;

-- Dimension: one row per country
CREATE TABLE countries (
    country_id       INT          NOT NULL,
    country_code     VARCHAR(3)   NOT NULL,
    country_name     VARCHAR(100) NOT NULL,
    region           VARCHAR(60)  NOT NULL,
    income_group     VARCHAR(40)  NOT NULL,
    lending_category VARCHAR(20)  NOT NULL,
    PRIMARY KEY (country_id),
    UNIQUE KEY uq_country_code (country_code)
) ENGINE=InnoDB;

-- Dimension: one row per debt indicator (World Bank series)
CREATE TABLE indicators (
    indicator_id    INT          NOT NULL,
    indicator_code  VARCHAR(30)  NOT NULL,
    indicator_name  VARCHAR(255) NOT NULL,
    indicator_group VARCHAR(40)  NOT NULL,
    PRIMARY KEY (indicator_id),
    UNIQUE KEY uq_indicator_code (indicator_code),
    KEY idx_indicator_group (indicator_group)
) ENGINE=InnoDB;

-- Fact: one debt value per (country, indicator)
CREATE TABLE debt_data (
    debt_id          INT    NOT NULL,
    country_id       INT    NOT NULL,
    indicator_id     INT    NOT NULL,
    debt_usd         DOUBLE NOT NULL,
    debt_billion_usd DOUBLE NOT NULL,
    PRIMARY KEY (debt_id),
    UNIQUE KEY uq_country_indicator (country_id, indicator_id),
    KEY idx_indicator (indicator_id),
    CONSTRAINT fk_debt_country   FOREIGN KEY (country_id)   REFERENCES countries(country_id),
    CONSTRAINT fk_debt_indicator FOREIGN KEY (indicator_id) REFERENCES indicators(indicator_id)
) ENGINE=InnoDB;

-- 1:1 extension of countries: macro-economic context (not debt)
CREATE TABLE country_macro (
    country_id          INT    NOT NULL,
    gni_usd             DOUBLE NULL,
    exports_usd         DOUBLE NULL,
    imports_usd         DOUBLE NULL,
    reserves_usd        DOUBLE NULL,
    current_account_usd DOUBLE NULL,
    PRIMARY KEY (country_id),
    CONSTRAINT fk_macro_country FOREIGN KEY (country_id) REFERENCES countries(country_id)
) ENGINE=InnoDB;

-- Reusable view used by Q25, Streamlit and Power BI
CREATE VIEW vw_top10_countries AS
SELECT c.country_name, c.country_code,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name, c.country_code
ORDER BY total_debt_billion DESC
LIMIT 10;

-- One row per country: external debt stock vs economy size
CREATE VIEW vw_country_debt_profile AS
SELECT c.country_id, c.country_name, c.country_code, c.region, c.income_group,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       ROUND(SUM(CASE WHEN i.indicator_code = 'DT.DOD.DECT.CD' THEN d.debt_usd ELSE 0 END) / 1e9, 4)
           AS external_debt_stock_billion,
       ROUND(m.gni_usd / 1e9, 4) AS gni_billion,
       ROUND(SUM(CASE WHEN i.indicator_code = 'DT.DOD.DECT.CD' THEN d.debt_usd ELSE 0 END) * 100.0
             / NULLIF(m.gni_usd, 0), 2) AS debt_to_gni_pct
FROM debt_data d
JOIN countries  c ON d.country_id   = c.country_id
JOIN indicators i ON d.indicator_id = i.indicator_id
LEFT JOIN country_macro m ON m.country_id = c.country_id
GROUP BY c.country_id, c.country_name, c.country_code, c.region, c.income_group, m.gni_usd;
