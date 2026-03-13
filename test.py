import duckdb

con = duckdb.connect("TP1_Wikipedia/sp500.duckdb")
df = con.execute("SELECT gics_sub_industry, headquarters_location FROM sp500_companies LIMIT 10").fetchdf()
con.close()

print(df)