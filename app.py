from flask import Flask, render_template, request, jsonify
from config import Config
from database import init_db, query_db
import math

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database when app starts
with app.app_context():
    init_db()

# BRAC formula implementation
def calculate_nutrient(mrn, opt_med, stv):
    try:
        nr = mrn - ((mrn / opt_med) * stv)
        return max(0, round(nr, 2))
    except ZeroDivisionError:
        return mrn

# Load soil optimum values
def get_soil_opt_med_values():
    return {
        'phosphorus_rice': 30,
        'phosphorus_other': 36,
        'potassium': 0.36,
        'zinc': 1.62
    }

# Get the appropriate Opt/Med value based on nutrient and crop type
def get_opt_med_value(nutrient, crop_name):
    opt_med_values = get_soil_opt_med_values()
    
    if nutrient == 'phosphorus':
        if 'ধান' in crop_name or 'আমন' in crop_name or 'আউশ' in crop_name:
            return opt_med_values['phosphorus_rice']
        else:
            return opt_med_values['phosphorus_other']
    else:
        nutrient_key = nutrient.lower()
        return opt_med_values.get(nutrient_key, 0)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/locations')
def get_locations():
    # Get unique locations from database
    results = query_db("SELECT DISTINCT region FROM fertilizer_recommendations ORDER BY region")
    
    if results is None:
        return jsonify([])
    
    locations = [result['region'] for result in results]
    return jsonify(locations)

@app.route('/api/fields/<location>')
def get_fields(location):
    # Get field data for the selected location
    results = query_db(
        "SELECT DISTINCT field_no FROM fertilizer_recommendations WHERE region = %s ORDER BY field_no",
        (location,)
    )
    
    if results is None:
        return jsonify([])
    
    fields = []
    for result in results:
        field_id = result['field_no']
        
        # Get season data for this field
        season_results = query_db(
            "SELECT season, crop, yield_target FROM fertilizer_recommendations WHERE region = %s AND field_no = %s",
            (location, field_id)
        )
        
        seasons = {}
        for season_row in season_results:
            season = season_row['season']
            
            # Special handling for field 13 with combined yield targets
            if field_id == 13 and isinstance(season_row['yield_target'], str) and 'এবং' in season_row['yield_target']:
                seasons[season] = {
                    'crop': season_row['crop'],
                    'yield_target': season_row['yield_target'],
                    'is_combined': True
                }
            else:
                # For other fields, convert to float
                try:
                    yield_target = float(season_row['yield_target']) if season_row['yield_target'] and str(season_row['yield_target']) != '0' else 0.0
                except (ValueError, TypeError):
                    yield_target = 0.0
                
                seasons[season] = {
                    'crop': season_row['crop'],
                    'yield_target': yield_target,
                    'is_combined': False
                }
        
        fields.append({
            'field_id': field_id,
            'seasons': seasons
        })
    
    return jsonify(fields)

@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    # Get field data from database
    results = query_db(
        """SELECT season, crop, yield_target, urea, tsp_dap, mop, gypsum, 
                  magnesium_sulfate, zinc_sulfate, boric_acid, organic_manure 
           FROM fertilizer_recommendations 
           WHERE region = %s AND field_no = %s""",
        (data['location'], data['field_id'])
    )
    
    if not results:
        return jsonify({"error": "জমি নং পাওয়া যায়নি"})
    
    recommendations = {}
    
    # Determine which seasons to process
    seasons_to_process = []
    if any(row['season'] == 'বছর ব্যাপী' for row in results):
        seasons_to_process = ['বছর ব্যাপী']
    else:
        seasons_to_process = ['রবি', 'খরিফ-১', 'খরিফ-২']
    
    for season in seasons_to_process:
        season_data = next((row for row in results if row['season'] == season), None)
        
        if not season_data:
            continue
            
        if season_data['crop'] == 'পতিত':
            recommendations[season] = {'fallow': True}
            continue
        
        # Handle yield target based on field type
        yield_target = season_data['yield_target']
        
        # For field 13, keep the yield target as string with "এবং"
        if data['field_id'] == 13 and isinstance(yield_target, str) and 'এবং' in yield_target:
            yield_target_value = yield_target
            is_combined = True
        else:
            try:
                yield_target_value = float(yield_target) if yield_target else 0
                is_combined = False
            except (ValueError, TypeError):
                yield_target_value = 0
                is_combined = False
        
        # Base recommendation - convert all values to native types
        rec = {
            'crop': season_data['crop'],
            'yield_target': yield_target_value,
            'is_combined': is_combined,
            'urea': float(season_data['urea']) if season_data['urea'] else 0,
            'tsp': float(season_data['tsp_dap']) if season_data['tsp_dap'] else 0,
            'mop': float(season_data['mop']) if season_data['mop'] else 0,
            'gypsum': float(season_data['gypsum']) if season_data['gypsum'] else 0,
            'magnesium_sulfate': float(season_data['magnesium_sulfate']) if season_data['magnesium_sulfate'] else 0,
            'zinc_sulfate': float(season_data['zinc_sulfate']) if season_data['zinc_sulfate'] else 0,
            'boric_acid': float(season_data['boric_acid']) if season_data['boric_acid'] else 0,
            'organic_manure': float(season_data['organic_manure']) if season_data['organic_manure'] else 0
        }
        
        # Apply soil test adjustment if provided (skip for combined field 13)
        if data.get('soil_test') and not is_combined:
            soil_values = data['soil_test']
            
            # Adjust nutrients based on soil test
            if 'phosphorus' in soil_values:
                opt_med = get_opt_med_value('phosphorus', rec['crop'])
                rec['tsp'] = calculate_nutrient(rec['tsp'], opt_med, soil_values['phosphorus'])
            
            if 'potassium' in soil_values:
                opt_med = get_opt_med_value('potassium', rec['crop'])
                rec['mop'] = calculate_nutrient(rec['mop'], opt_med, soil_values['potassium'])
            
            if 'zinc' in soil_values:
                opt_med = get_opt_med_value('zinc', rec['crop'])
                rec['zinc_sulfate'] = calculate_nutrient(rec['zinc_sulfate'], opt_med, soil_values['zinc'])
        
        # Apply DAP substitution if requested (skip for combined field 13)
        if data.get('use_dap') and not is_combined:
            urea_reduction = rec['tsp'] * 0.4
            rec['urea'] = max(0, rec['urea'] - urea_reduction)
            rec['dap'] = rec.pop('tsp')  # Rename to DAP
        
        # Apply land area scaling
        land_area = data.get('land_area', 1)
        for key in ['urea', 'tsp', 'mop', 'gypsum', 'magnesium_sulfate', 'zinc_sulfate', 'boric_acid', 'dap']:
            if key in rec:
                rec[key] = rec[key] * land_area
        rec['organic_manure'] = rec['organic_manure'] * land_area
        
        recommendations[season] = rec
    
    return jsonify(recommendations)

if __name__ == '__main__':
    app.run(debug=True)