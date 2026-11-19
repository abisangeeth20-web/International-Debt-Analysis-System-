-- ==================================================================
-- ADVANCED SQL QUERIES (Q21-Q30)
-- Concepts: window functions with PARTITION BY, running totals,
--           CASE bucketing, views, nested subqueries
-- ==================================================================
USE international_debt;

-- Q21: Find the top 5 indicators contributing most to global debt.
-- Why: which debt measures dominate the global total, with % share.
SELECT i.indicator_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       ROUND(SUM(d.debt_usd) * 100.0 / (SELECT SUM(debt_usd) FROM debt_data), 2) AS pct_of_global
FROM debt_data d
JOIN indicators i ON d.indicator_id = i.indicator_id
GROUP BY i.indicator_name
ORDER BY total_debt_billion DESC
LIMIT 5;

-- Q22: Calculate percentage contribution of each country to total global debt.
-- Why: measures how concentrated global debt is.
SELECT c.country_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       ROUND(SUM(d.debt_usd) * 100.0 / (SELECT SUM(debt_usd) FROM debt_data), 4) AS pct_of_global
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY pct_of_global DESC;

-- Q23: Identify the top 3 countries for each indicator based on debt.
-- Why: PARTITION BY restarts the ranking for every indicator.
SELECT indicator_name, country_name, debt_billion, country_rank
FROM (
    SELECT i.indicator_name, c.country_name,
           ROUND(d.debt_usd / 1e9, 4) AS debt_billion,
           ROW_NUMBER() OVER (PARTITION BY i.indicator_id ORDER BY d.debt_usd DESC) AS country_rank
    FROM debt_data d
    JOIN countries  c ON d.country_id   = c.country_id
    JOIN indicators i ON d.indicator_id = i.indicator_id
) ranked
WHERE country_rank <= 3
ORDER BY indicator_name, country_rank;

-- Q24: Find the difference between maximum and minimum debt for each country.
-- Why: a big range means one or two debt types dominate the country's profile.
SELECT c.country_name,
       ROUND(MAX(d.debt_usd) / 1e9, 4) AS max_debt_billion,
       ROUND(MIN(d.debt_usd) / 1e9, 6) AS min_debt_billion,
       ROUND((MAX(d.debt_usd) - MIN(d.debt_usd)) / 1e9, 4) AS debt_range_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY debt_range_billion DESC;

-- Q25: Create a view for the top 10 countries with highest debt.
-- Why: the view vw_top10_countries is created in sql/00_schema.sql:
--   CREATE VIEW vw_top10_countries AS SELECT c.country_name, c.country_code,
--   ROUND(SUM(d.debt_usd)/1e9,4) AS total_debt_billion FROM debt_data d JOIN countries c
--   ON d.country_id = c.country_id GROUP BY c.country_name, c.country_code
--   ORDER BY total_debt_billion DESC LIMIT 10;
-- This query reads from it.
SELECT * FROM vw_top10_countries;

-- Q26: Categorize countries into High, Medium and Low debt (based on thresholds).
-- Why: thresholds are the 75th / 25th percentiles of country totals:
-- High >= $588B, Medium >= $40B, Low < $40B.
SELECT c.country_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       CASE
           WHEN SUM(d.debt_usd) >= 588000000000 THEN 'High Debt'
           WHEN SUM(d.debt_usd) >= 40000000000  THEN 'Medium Debt'
           ELSE 'Low Debt'
       END AS debt_category
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt_billion DESC;

-- Q27: Use window functions to calculate cumulative debt per country.
-- Why: running total and running % as countries are added from largest
-- to smallest (the data behind the Pareto chart).
SELECT c.country_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       ROUND(SUM(SUM(d.debt_usd)) OVER (ORDER BY SUM(d.debt_usd) DESC) / 1e9, 4) AS cumulative_debt_billion,
       ROUND(SUM(SUM(d.debt_usd)) OVER (ORDER BY SUM(d.debt_usd) DESC) * 100.0
             / SUM(SUM(d.debt_usd)) OVER (), 2) AS cumulative_pct
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt_billion DESC;

-- Q28: Find indicators where average debt is higher than overall average debt.
-- Why: HAVING with a scalar subquery.
SELECT i.indicator_name, ROUND(AVG(d.debt_usd) / 1e9, 4) AS avg_debt_billion
FROM debt_data d
JOIN indicators i ON d.indicator_id = i.indicator_id
GROUP BY i.indicator_name
HAVING AVG(d.debt_usd) > (SELECT AVG(debt_usd) FROM debt_data)
ORDER BY avg_debt_billion DESC;

-- Q29: Identify countries contributing more than 5% of global debt.
-- Why: the few countries that move the global total.
SELECT c.country_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion,
       ROUND(SUM(d.debt_usd) * 100.0 / (SELECT SUM(debt_usd) FROM debt_data), 4) AS pct_of_global
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
HAVING SUM(d.debt_usd) * 100.0 / (SELECT SUM(debt_usd) FROM debt_data) > 5
ORDER BY pct_of_global DESC;

-- Q30: Find the most dominant indicator (highest contribution) for each country.
-- Why: each country's #1 debt measure and its share of that country's total.
SELECT country_name, indicator_name, debt_billion, pct_of_country
FROM (
    SELECT c.country_name, i.indicator_name,
           ROUND(d.debt_usd / 1e9, 4) AS debt_billion,
           ROUND(d.debt_usd * 100.0 / SUM(d.debt_usd) OVER (PARTITION BY d.country_id), 2) AS pct_of_country,
           ROW_NUMBER() OVER (PARTITION BY d.country_id ORDER BY d.debt_usd DESC) AS rn
    FROM debt_data d
    JOIN countries  c ON d.country_id   = c.country_id
    JOIN indicators i ON d.indicator_id = i.indicator_id
) ranked
WHERE rn = 1
ORDER BY debt_billion DESC;
