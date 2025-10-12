import os.path

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, VARCHAR

if not os.path.exists("nekona"):
    os.mkdir("nekona")

engine = create_engine("sqlite:///data/nekona.db", echo=True)

md_obj = MetaData()

# Declare tables

server_settings = Table(
    "server_settings",
    md_obj,
    Column("uid", Integer, primary_key=True),
    Column("name", VARCHAR, primary_key=True),
    Column("value", VARCHAR)
)

leveling = Table(
    "leveling",
    md_obj,
    Column("uid", Integer, primary_key=True),
    Column("gid", Integer, primary_key=True),
    Column("xp", Integer)
)

md_obj.create_all(engine, checkfirst=True)
