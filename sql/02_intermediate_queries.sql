-- ==================================================================
-- INTERMEDIATE SQL QUERIES (Q11-Q20)
-- Concepts: GROUP BY, HAVING, multi-table JOINs, subqueries, RANK()
-- ==================================================================
USE international_debt;

-- Q11: Find the total debt for each country.
-- Why: the base country-wise debt distribution.
SELECT c.country_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt_billion DESC;

-- Q12: Display the top 10 countries with the highest total debt.
-- Why: the most indebted countries in the dataset.
SELECT c.country_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt_billion DESC
LIMIT 10;

-- Q13: Find the average debt per country.
-- Why: average size of one debt record per country (scale-independent of record count).
SELECT c.country_name, ROUND(AVG(d.debt_usd) / 1e9, 4) AS avg_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY avg_debt_billion DESC;

-- Q14: Calculate total debt for each indicator.
-- Why: indicator-wise debt distribution.
SELECT i.indicator_name, i.indicator_group, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN indicators i ON d.indicator_id = i.indicator_id
GROUP BY i.indicator_name, i.indicator_group
ORDER BY total_debt_billion DESC;

-- Q15: Identify the indicator contributing the highest total debt.
-- Why: the single biggest debt measure across all countries.
SELECT i.indicator_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN indicators i ON d.indicator_id = i.indicator_id
GROUP BY i.indicator_name
ORDER BY total_debt_billion DESC
LIMIT 1;

-- Q16: Find the country with the lowest total debt.
-- Why: the least indebted country in the dataset.
SELECT c.country_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY total_debt_billion ASC
LIMIT 1;

-- Q17: Calculate total debt for each country and indicator combination.
-- Why: the full country x indicator matrix (largest combinations first).
SELECT c.country_name, i.indicator_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries  c ON d.country_id   = c.country_id
JOIN indicators i ON d.indicator_id = i.indicator_id
GROUP BY c.country_name, i.indicator_name
ORDER BY total_debt_billion DESC;

-- Q18: Count how many indicators each country has.
-- Why: breadth of each country's debt reporting.
SELECT c.country_name, COUNT(DISTINCT d.indicator_id) AS indicator_count
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY indicator_count DESC, c.country_name;

-- Q19: Display countries whose total debt is above the global average.
-- Why: HAVING + nested subquery; the average is the mean of country totals.
SELECT c.country_name, ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
HAVING SUM(d.debt_usd) > (
    SELECT AVG(country_total)
    FROM (SELECT SUM(debt_usd) AS country_total FROM debt_data GROUP BY country_id) AS t
)
ORDER BY total_debt_billion DESC;

-- Q20: Rank countries based on total debt (highest to lowest).
-- Why: RANK() window function over an aggregate.
SELECT RANK() OVER (ORDER BY SUM(d.debt_usd) DESC) AS debt_rank,
       c.country_name,
       ROUND(SUM(d.debt_usd) / 1e9, 4) AS total_debt_billion
FROM debt_data d
JOIN countries c ON d.country_id = c.country_id
GROUP BY c.country_name
ORDER BY debt_rank;
