"""Basic usage examples for sqlmeta."""

from sqlmeta import Table, SqlColumn, SqlConstraint, ConstraintType

# Create a table
users_table = Table(
    name="users",
    schema="public",
    columns=[
        SqlColumn("id", "SERIAL", is_primary_key=True),
        SqlColumn("email", "VARCHAR(255)", is_nullable=False),
        SqlColumn("name", "VARCHAR(100)", is_nullable=False),
        SqlColumn("created_at", "TIMESTAMP", default_value="CURRENT_TIMESTAMP"),
    ],
    constraints=[
        SqlConstraint(
            constraint_type=ConstraintType.UNIQUE,
            name="uq_users_email",
            column_names=["email"]
        )
    ]
)

# Print CREATE TABLE statement
print(users_table.create_statement)

# Export to dictionary
table_dict = users_table.to_dict()
print(f"\nTable as dict: {table_dict}")

# Recreate from dictionary
users_table_copy = Table.from_dict(table_dict)
print(f"\nRecreated table: {users_table_copy.name}")
