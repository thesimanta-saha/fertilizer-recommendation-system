import psycopg2
from config import Config
import pandas as pd
import re

def get_connection():
    """Create a connection to the PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            port=Config.DB_PORT
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def bengali_to_english_number(bengali_num):
    """Convert Bengali numerals to English numerals"""
    bengali_digits = {
        '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
        '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
    }
    
    if isinstance(bengali_num, str):
        # Convert each Bengali digit to English
        result = ''
        for char in bengali_num:
            if char in bengali_digits:
                result += bengali_digits[char]
            else:
                result += char
        return result
    return bengali_num

def init_db():
    """Initialize the database with data from CSV"""
    conn = get_connection()
    if conn is None:
        return False
    
    try:
        # Read the CSV file
        df = pd.read_csv('data/fertilizer_recommendation_sample.csv', encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        
        # Convert Bengali numerals to English for all numeric columns
        numeric_columns = [
            'জমি নং', 
            'লক্ষ্যমাত্রা ফলন (কেজি/শতাংশ)',
            'ইউরিয়া (গ্রাম/শতাংশ)',
            'টিএসপি/ডিএপি (গ্রাম/শতাংশ)',
            'এমওপি (গ্রাম/শতাংশ)',
            'জিপসাম (গ্রাম/শতাংশ)',
            'ম্যাগনেসিয়াম সালফেট (গ্রাম/শতাংশ)',
            'জিঙ্ক সালফেট (হেপ্টা হাইড্রেট) (গ্রাম/শতাংশ)',
            'বোরিক এসিড (গ্রাম/শতাংশ)',
            'জৈবসার (কেজি/শতাংশ)'
        ]
        
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].apply(bengali_to_english_number)
        
        # Insert data into database
        cur = conn.cursor()
        
        # Clear existing data
        cur.execute("DELETE FROM fertilizer_recommendations")
        
        # Insert new data
        for _, row in df.iterrows():
            # Handle special case for field 13 with combined yield targets
            yield_target = row['লক্ষ্যমাত্রা ফলন (কেজি/শতাংশ)']
            field_no = int(row['জমি নং'])
            
            # For field 13, keep the combined yield target as string
            if field_no == 13 and 'এবং' in str(yield_target):
                # Don't convert to float, keep as string
                pass
            else:
                # Convert to numeric for other fields
                try:
                    yield_target = float(yield_target) if yield_target and yield_target != '0' else 0.0
                except (ValueError, TypeError):
                    yield_target = 0.0
            
            # Handle numeric conversions for all other fields
            urea = float(row['ইউরিয়া (গ্রাম/শতাংশ)']) if row['ইউরিয়া (গ্রাম/শতাংশ)'] and row['ইউরিয়া (গ্রাম/শতাংশ)'] != '0' else 0.0
            tsp_dap = float(row['টিএসপি/ডিএপি (গ্রাম/শতাংশ)']) if row['টিএসপি/ডিএপি (গ্রাম/শতাংশ)'] and row['টিএসপি/ডিএপি (গ্রাম/শতাংশ)'] != '0' else 0.0
            mop = float(row['এমওপি (গ্রাম/শতাংশ)']) if row['এমওপি (গ্রাম/শতাংশ)'] and row['এমওপি (গ্রাম/শতাংশ)'] != '0' else 0.0
            gypsum = float(row['জিপসাম (গ্রাম/শতাংশ)']) if row['জিপসাম (গ্রাম/শতাংশ)'] and row['জিপসাম (গ্রাম/শতাংশ)'] != '0' else 0.0
            magnesium_sulfate = float(row['ম্যাগনেসিয়াম সালফেট (গ্রাম/শতাংশ)']) if row['ম্যাগনেসিয়াম সালফেট (গ্রাম/শতাংশ)'] and row['ম্যাগনেসিয়াম সালফেট (গ্রাম/শতাংশ)'] != '0' else 0.0
            zinc_sulfate = float(row['জিঙ্ক সালফেট (হেপ্টা হাইড্রেট) (গ্রাম/শতাংশ)']) if row['জিঙ্ক সালফেট (হেপ্টা হাইড্রেট) (গ্রাম/শতাংশ)'] and row['জিঙ্ক সালফেট (হেপ্টা হাইড্রেট) (গ্রাম/শতাংশ)'] != '0' else 0.0
            boric_acid = float(row['বোরিক এসিড (গ্রাম/শতাংশ)']) if row['বোরিক এসিড (গ্রাম/শতাংশ)'] and row['বোরিক এসিড (গ্রাম/শতাংশ)'] != '0' else 0.0
            organic_manure = float(row['জৈবসার (কেজি/শতাংশ)']) if row['জৈবসার (কেজি/শতাংশ)'] and row['জৈবসার (কেজি/শতাংশ)'] != '0' else 0.0
            
            cur.execute(
                """INSERT INTO fertilizer_recommendations 
                (field_no, season, region, crop, yield_target, urea, tsp_dap, mop, gypsum, magnesium_sulfate, zinc_sulfate, boric_acid, organic_manure)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    field_no,
                    row['মৌসুম'],
                    row['অঞ্চল'],
                    row['ফসল'],
                    yield_target,
                    urea,
                    tsp_dap,
                    mop,
                    gypsum,
                    magnesium_sulfate,
                    zinc_sulfate,
                    boric_acid,
                    organic_manure
                )
            )
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

def query_db(query, params=None):
    """Execute a query and return results"""
    conn = get_connection()
    if conn is None:
        return None
    
    try:
        cur = conn.cursor()
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        # For SELECT queries, return results
        if query.strip().upper().startswith('SELECT'):
            columns = [desc[0] for desc in cur.description]
            results = []
            for row in cur.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        else:
            conn.commit()
            return cur.rowcount
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error executing query: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return None