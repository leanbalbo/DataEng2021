# this program loads Census ACS data using basic, slow INSERTs 
# run it with -h to see the command line options

import time
import psycopg2
import argparse
import re
import csv

DBname = "in_class_activity"
DBuser = "learn_postsql"
DBpwd = "xuexihaha"
TableName = 'CensusData'
Datafile = "acs2017_census_tract_data.csv"  # name of the data file to be loaded
CreateDB = False  # indicates whether the DB table should be (re)-created
Year = 2017

def row2vals(row):
	# handle the null vals
	for key in row:
		if not row[key]:
			row[key] = 0
		row['County'] = row['County'].replace('\'','')  # eliminate quotes within literals

	ret = f"""
       {Year},                          -- Year
       {row['CensusTract']},            -- CensusTract
       '{row['State']}',                -- State
       '{row['County']}',               -- County
       {row['TotalPop']},               -- TotalPop
       {row['Men']},                    -- Men
       {row['Women']},                  -- Women
       {row['Hispanic']},               -- Hispanic
       {row['White']},                  -- White
       {row['Black']},                  -- Black
       {row['Native']},                 -- Native
       {row['Asian']},                  -- Asian
       {row['Pacific']},                -- Pacific
       {row['Citizen']},                -- Citizen
       {row['Income']},                 -- Income
       {row['IncomeErr']},              -- IncomeErr
       {row['IncomePerCap']},           -- IncomePerCap
       {row['IncomePerCapErr']},        -- IncomePerCapErr
       {row['Poverty']},                -- Poverty
       {row['ChildPoverty']},           -- ChildPoverty
       {row['Professional']},           -- Professional
       {row['Service']},                -- Service
       {row['Office']},                 -- Office
       {row['Construction']},           -- Construction
       {row['Production']},             -- Production
       {row['Drive']},                  -- Drive
       {row['Carpool']},                -- Carpool
       {row['Transit']},                -- Transit
       {row['Walk']},                   -- Walk
       {row['OtherTransp']},            -- OtherTransp
       {row['WorkAtHome']},             -- WorkAtHome
       {row['MeanCommute']},            -- MeanCommute
       {row['Employed']},               -- Employed
       {row['PrivateWork']},            -- PrivateWork
       {row['PublicWork']},             -- PublicWork
       {row['SelfEmployed']},           -- SelfEmployed
       {row['FamilyWork']},             -- FamilyWork
       {row['Unemployment']}            -- Unemployment
	"""
	return ret


def initialize():
  global Year

  parser = argparse.ArgumentParser()
  parser.add_argument("-d", "--datafile", required=True)
  parser.add_argument("-c", "--createtable", action="store_true")
  parser.add_argument("-y", "--year", default=Year)
  args = parser.parse_args()

  global Datafile
  Datafile = args.datafile
  global CreateDB
  CreateDB = args.createtable
  Year = args.year

# read the input data file into a list of row strings
# skip the header row
def readdata(fname):
	print(f"readdata: reading from File: {fname}")
	with open(fname, mode="r") as fil:
		dr = csv.DictReader(fil)
		headerRow = next(dr)
		# print(f"Header: {headerRow}")

		rowlist = []
		for row in dr:
			rowlist.append(row)

	return rowlist

# convert list of data rows into list of SQL 'INSERT INTO ...' commands
def getSQLcmnds(rowlist):
	cmdlist = []
	for row in rowlist:
		valstr = row2vals(row)
		cmd = f"INSERT INTO {TableName} VALUES ({valstr});"
		cmdlist.append(cmd)
	return cmdlist

# connect to the database
def dbconnect():
	connection = psycopg2.connect(
        host="localhost",
        database=DBname,
        user=DBuser,
        password=DBpwd,
	)
	connection.autocommit = True
	return connection

# create the target table 
# assumes that conn is a valid, open connection to a Postgres database
def createTable(conn):

	with conn.cursor() as cursor:
		cursor.execute(f"""
        	DROP TABLE IF EXISTS {TableName};
        	CREATE TABLE {TableName} (
            	Year                INTEGER,
                CensusTract         NUMERIC,
            	State               TEXT,
            	County              TEXT,
            	TotalPop            INTEGER,
            	Men                 INTEGER,
            	Women               INTEGER,
            	Hispanic            DECIMAL,
            	White               DECIMAL,
            	Black               DECIMAL,
            	Native              DECIMAL,
            	Asian               DECIMAL,
            	Pacific             DECIMAL,
            	citizen             DECIMAL,
            	Income              DECIMAL,
            	IncomeErr           DECIMAL,
            	IncomePerCap        DECIMAL,
            	IncomePerCapErr     DECIMAL,
            	Poverty             DECIMAL,
            	ChildPoverty        DECIMAL,
            	Professional        DECIMAL,
            	Service             DECIMAL,
            	Office              DECIMAL,
            	Construction        DECIMAL,
            	Production          DECIMAL,
            	Drive               DECIMAL,
            	Carpool             DECIMAL,
            	Transit             DECIMAL,
            	Walk                DECIMAL,
            	OtherTransp         DECIMAL,
            	WorkAtHome          DECIMAL,
            	MeanCommute         DECIMAL,
            	Employed            INTEGER,
            	PrivateWork         DECIMAL,
            	PublicWork          DECIMAL,
            	SelfEmployed        DECIMAL,
            	FamilyWork          DECIMAL,
            	Unemployment        DECIMAL
         	);	
         	ALTER TABLE {TableName} ADD PRIMARY KEY (Year, CensusTract);
         	CREATE INDEX idx_{TableName}_State ON {TableName}(State);
    	""")

		print(f"Created {TableName}")


def clean_csv_value(value) -> str:
    if value is None:
        return r'\N'
    return str(value).replace('\n', '\\n')

from typing import Iterator, Optional
import io

class StringIteratorIO(io.TextIOBase):
    def __init__(self, iter: Iterator[str]):
        self._iter = iter
        self._buff = ''

    def readable(self) -> bool:
        return True

    def _read1(self, n: Optional[int] = None) -> str:
        while not self._buff:
            try:
                self._buff = next(self._iter)
            except StopIteration:
                break
        ret = self._buff[:n]
        self._buff = self._buff[len(ret):]
        return ret

    def read(self, n: Optional[int] = None) -> str:
        line = []
        if n is None or n < 0:
            while True:
                m = self._read1()
                if not m:
                    break
                line.append(m)
        else:
            while n > 0:
                m = self._read1(n)
                if not m:
                    break
                n -= len(m)
                line.append(m)
        return ''.join(line)

def copy_string_iterator(connection, all_rows, size):
    with connection.cursor() as cursor:
        print(f"Loading {size} rows")
        start = time.perf_counter()
        rows_string_iterator = StringIteratorIO((
            '|'.join(map(clean_csv_value, (
		'2017',
                row['CensusTract'],
                row['State'],
                row['County'],
                row['TotalPop'],
                row['Men'],
                row['Women'],
                row['Hispanic'],
                row['White'],
                row['Black'],
                row['Native'],
                row['Asian'],
                row['Pacific'],
                row['Citizen'],
                row['Income'],
                row['IncomeErr'],
				row['IncomePerCap'],
				row['IncomePerCapErr'],
				row['Poverty'],
				row['ChildPoverty'],
				row['Professional'],
				row['Service'],
				row['Office'],
				row['Construction'],
				row['Production'],
				row['Drive'],
				row['Carpool'],
				row['Transit'],
				row['Walk'],
				row['OtherTransp'],
				row['WorkAtHome'],
				row['MeanCommute'],
				row['Employed'],
				row['PrivateWork'],
				row['PublicWork'],
				row['SelfEmployed'],
				row['FamilyWork'],
				row['Unemployment']
            ))) + '\n'
            for row in all_rows
        ))
        cursor.copy_from(rows_string_iterator, f'{TableName}', sep='|')
        elapsed = time.perf_counter() - start
        print(f'Finished Loading. Elapsed Time: {elapsed:0.4} seconds')

def load(conn, icmdlist):

	with conn.cursor() as cursor:
		print(f"Loading {len(icmdlist)} rows")
		start = time.perf_counter()
    
		for cmd in icmdlist:
			# print (cmd)
			cursor.execute(cmd)

		elapsed = time.perf_counter() - start
		print(f'Finished Loading. Elapsed Time: {elapsed:0.4} seconds')


def main():
    initialize()
    conn = dbconnect()
    rlis = readdata(Datafile)
    cmdlist = getSQLcmnds(rlis)

    if CreateDB:
    	createTable(conn)

    copy_string_iterator(conn, iter(rlis), len(rlis))

#    load(conn, cmdlist)


if __name__ == "__main__":
    main()



