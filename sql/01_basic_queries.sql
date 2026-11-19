-- ==================================================================
-- BASIC SQL QUERIES (Q1-Q10)
-- Concepts: SELECT, DISTINCT, COUNT, JOIN, WHERE, ORDER BY, LIMIT,
--           aggregate functions (MIN / MAX / AVG / SUM)
-- Runs on MySQL 8 (database international_debt) and on the bundled
-- SQLite copy used by the Streamlit app.
-- ==================================================================
USE international_debt;

-- Q1: Retrieve all distinct country names from the dataset.
-- Why: checks coverage and fills the country filter in the dashboard.
SELECT DISTINCT country_name
FROM countries
ORDER BY country_name;

-- Q2: Count the total number of countries available.
-- Why: headline KPI card.
SELECT COUNT(DISTINCT country_id) AS total_countries
FROM countries;

-- Q3: Find the total number of indicators present.
-- Why: headline KPI card; shows how many debt measures are tracked.
SELECT COUNT(DISTINCT indicator_id) AS total_indicators
FROM indicators;

-- Q4: Display the first 10 records of the dataset.
-- Why: confirms the fact table joins correctly to both dimensions.
SELECT d.debt_id, c.country_name, i.indicator_name, d.debt_usd
FROM debt_data d
JOIN countries  c ON d.country_id   = c.country_id
JOIN indicators i ON d.indicator_id = i.indicator_id
ORDER BY d.debt_id
LIMIT 10;

-- Q5: Calculate the total global debt.
-- Why: headline KPI (sum of every debt indicator for every country).
SELECT ROUND(SUM(debt_usd), 2)        AS total_debt_usd,
       ROUND(SUM(debt_usd) / 1e12, 4) AS total_debt_trillion
FROM debt_data;

-- Q6: List all unique indicator names.
-- Why: the catalogue of debt measures available for analysis.
SELECT DISTINCT indicator_name, indicator_group
FROM indicators
ORDER BY indicator_group, indicator_name;

-- Q7: Find the number of records for each country.
-- Why: shows reporting completeness; fewer records = fewer debt types reported.
SELECT c.country_name, COUNT(d.debt_id) AS record_count
FROM countries c
JOIN debt_data d ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY record_count DESC, c.country_name;

-- Q8: Display all records where debt is greater than 1 billion USD.
-- Why: isolates the material debt positions.
SELECT c.country_name, i.indicator_name,
       ROUND(d.debt_usd / 1e9, 4) AS debt_billion
FROM debt_data d
JOIN countries  c ON d.country_id   = c.country_id
JOIN indicators i ON d.indicator_id = i.indicator_id
WHERE d.debt_usd > 1000000000
ORDER BY d.debt_usd DESC;

-- Q9: Find the minimum, maximum, and average debt values.
-- Why: the spread of single debt values (very right-skewed).
SELECT ROUND(MIN(debt_usd), 2)       AS min_debt_usd,
       ROUND(MAX(debt_usd) / 1e9, 4) AS max_debt_billion,
       ROUND(AVG(debt_usd) / 1e9, 4) AS avg_debt_billion
FROM debt_data;

-- Q10: Count total number of records in the dataset.
-- Why: size of the cleaned fact table.
SELECT COUNT(*) AS total_records
FROM debt_data;
