import pandas as pd

df = pd.read_excel("District STAFF Profile.xlsx")

columns_to_keep = [
    'DISTRICT',
    'DISTNAME',
    'District 2024 Staff: Teacher Total Full Time Equiv Count',
    'District 2024 Staff: Teacher Beginning Full Time Equiv Count',
    'District 2024 Staff: Teacher 1-5 Years Full Time Equiv Count',
    'District 2024 Staff: Teacher 6-10 Years Full Time Equiv Count',
    'District 2024 Staff: Teacher 11-20 Years Full Time Equiv Count',
    'District 2024 Staff: Teacher 21-30 Years Full Time Equiv Count',
    'District 2024 Staff: Teacher > 30 Years Full Time Equiv Count',
       'District 2024 Staff: Teacher Turnover Ratio',
       'District 2024 Staff: Average Years Experience of Teachers with District',
       'District 2024 Staff: Teacher Experience Average',

       'District 2024 Staff: Teacher Student Ratio',
       'District 2024 Staff: Teacher Beginning Base Salary Average',
       'District 2024 Staff: Teacher 1-5 Years Base Salary Average',
       'District 2024 Staff: Teacher 6-10 Years Base Salary Average',
       'District 2024 Staff: Teacher 11-20 Years Base Salary Average',
       'District 2024 Staff: Teacher 21-30 Years Base Salary Average',
       'District 2024 Staff: Teacher > 30 Years Base Salary Average',
       'District 2024 Staff: Teacher Total Base Salary Average',
]

df = df[columns_to_keep]

df.to_excel("District Teacher Profile.xlsx", index=False)

df = pd.read_excel("CSTAF.xlsx")

# Rename columns in df using mapping from Campus_Staff_Information_2024_State.xlsx
mapping_df = pd.read_excel("Campus_Staff_Information_2024_State.xlsx", skiprows=4)
rename_mapping = mapping_df[['Name', 'Label']].dropna()
rename_dict = dict(zip(rename_mapping['Name'], rename_mapping['Label']))
df = df.rename(columns=rename_dict)

columns_to_keep = [
    'CAMPUS', 'DISTRICT', 'CAMPNAME', 'DISTNAME',
       'Campus 2024 Staff: Teacher Total Full Time Equiv Count',

       'Campus 2024 Staff: Teacher Beginning Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 1-5 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 6-10 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 11-20 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 21-30 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher > 30 Years Full Time Equiv Count',

       'Campus 2024 Staff: Teacher Total Base Salary Average',
       'Campus 2024 Staff: Teacher Beginning Base Salary Average',
       'Campus 2024 Staff: Teacher 1-5 Years Base Salary Average',
       'Campus 2024 Staff: Teacher 6-10 Years Base Salary Average',
       'Campus 2024 Staff: Teacher 11-20 Years Base Salary Average',
       'Campus 2024 Staff: Teacher 21-30 Years Base Salary Average',
       'Campus 2024 Staff: Teacher > 30 Years Base Salary Average',

       'Campus 2024 Staff: Teacher Beginning Full Time Equiv Percent',
       'Campus 2024 Staff: Teacher 1-5 Years Full Time Equiv Percent',
       'Campus 2024 Staff: Teacher 6-10 Years Full Time Equiv Percent',
       'Campus 2024 Staff: Teacher 11-20 Years Full Time Equiv Percent',
       'Campus 2024 Staff: Teacher 21-30 Years Full Time Equiv Percent',
       'Campus 2024 Staff: Teacher > 30 Years Full Time Equiv Percent',
        'Campus 2024 Staff: Teacher Tenure Average',
        'Campus 2024 Staff: Teacher Experience Average',
       'Campus 2024 Staff: Teacher Student Ratio'
]

df = df[columns_to_keep]



# Define salary columns to clean (for use in missing data report and cleaning) - use original column names with prefix
salary_columns_to_clean = [
'Campus 2024 Staff: Teacher Beginning Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 1-5 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 6-10 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 11-20 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher 21-30 Years Full Time Equiv Count',
       'Campus 2024 Staff: Teacher > 30 Years Full Time Equiv Count',
    'Campus 2024 Staff: Teacher Beginning Base Salary Average',
    'Campus 2024 Staff: Teacher 1-5 Years Base Salary Average',
    'Campus 2024 Staff: Teacher 6-10 Years Base Salary Average',
    'Campus 2024 Staff: Teacher 11-20 Years Base Salary Average',
    'Campus 2024 Staff: Teacher 21-30 Years Base Salary Average',
    'Campus 2024 Staff: Teacher > 30 Years Base Salary Average',
    'Campus 2024 Staff: Teacher Total Base Salary Average',
]

# Report rows with missing salary data
missing_salary_rows = df[df[salary_columns_to_clean].isna().any(axis=1)]
missing_salary_rows.to_excel("Missing Teacher Salary Data.xlsx", index=False)

df.columns = df.columns.str.replace("Campus 2024 Staff: ", "", regex=False)


df = df.rename(columns={"CAMPUS": "School Number", "DISTRICT": "District Number"})


# Clean and convert ALL columns with "." to NaN where appropriate
df = df.replace('.', pd.NA)
df = df.apply(pd.to_numeric, errors='ignore')


# Set salary value to 0 if the corresponding Count is 0
for col in df.columns:
    if "Full Time Equiv Count" in col:
        salary_col = col.replace("Full Time Equiv Count", "Base Salary Average")
        if salary_col in df.columns:
            df.loc[df[col] == 0, salary_col] = 0

# Round relevant inputs to 1 decimal before further calculations
round_cols = [
    'Teacher 6-10 Years Full Time Equiv Count',
    'Teacher 11-20 Years Full Time Equiv Count',
    'Teacher 21-30 Years Full Time Equiv Count',
    'Teacher > 30 Years Full Time Equiv Count',
    'Teacher 6-10 Years Full Time Equiv Percent',
    'Teacher 11-20 Years Full Time Equiv Percent',
    'Teacher 21-30 Years Full Time Equiv Percent',
    'Teacher > 30 Years Full Time Equiv Percent',
    'Teacher 6-10 Years Base Salary Average',
    'Teacher 11-20 Years Base Salary Average',
    'Teacher 21-30 Years Base Salary Average',
    'Teacher > 30 Years Base Salary Average',
]
df[round_cols] = df[round_cols].round(1)

df["Teacher 5+ Years Full Time Equiv Count"] = (
    df['Teacher 6-10 Years Full Time Equiv Count'] +
    df['Teacher 11-20 Years Full Time Equiv Count'] +
    df['Teacher 21-30 Years Full Time Equiv Count'] +
    df['Teacher > 30 Years Full Time Equiv Count']
)

df["Teacher 5+ Years Full Time Equiv Percent"] = df['Teacher 6-10 Years Full Time Equiv Percent'] + df['Teacher 11-20 Years Full Time Equiv Percent'] + df['Teacher 21-30 Years Full Time Equiv Percent'] + df['Teacher > 30 Years Full Time Equiv Percent']

df["Teacher 5+ Years Base Salary Average"] = (
    (df['Teacher 6-10 Years Full Time Equiv Count'] * df['Teacher 6-10 Years Base Salary Average']) +
    (df['Teacher 11-20 Years Full Time Equiv Count'] * df['Teacher 11-20 Years Base Salary Average']) +
    (df['Teacher 21-30 Years Full Time Equiv Count'] * df['Teacher 21-30 Years Base Salary Average']) +
    (df['Teacher > 30 Years Full Time Equiv Count'] * df['Teacher > 30 Years Base Salary Average'])
) / df["Teacher 5+ Years Full Time Equiv Count"]

df["Teacher 5+ Years Base Salary Average"] = df["Teacher 5+ Years Base Salary Average"].fillna(0)

salary_columns_to_clean = [x.replace("Campus 2024 Staff: ", "") for x in salary_columns_to_clean]

# Replace salary values with "MASKED" if all are NaN in a row
mask_all_nan = df[salary_columns_to_clean].isna().all(axis=1)
# Set all columns containing "Teacher" in their name to "MASKED" for those rows
teacher_columns = [col for col in df.columns if "Teacher" in col]
df.loc[mask_all_nan, teacher_columns] = "MASKED"

df.to_excel("Campus Teacher Profile.xlsx", index=False)
