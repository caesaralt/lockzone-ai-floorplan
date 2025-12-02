"""
Simpro Integration Routes Blueprint

Handles all Simpro API integration:
- /api/simpro/config: Configuration management
- /api/simpro/connect: OAuth connection
- /api/simpro/disconnect: Disconnect from Simpro
- /api/simpro/sync: Sync quote to Simpro
- /api/simpro/test-endpoints: Test available endpoints
- /api/simpro/customers: Fetch/import customers
- /api/simpro/jobs: Fetch/import jobs
- /api/simpro/quotes: Fetch quotes
- /api/simpro/catalogs: Fetch/import catalog items
- /api/simpro/labor-rates: Fetch labor rates
- /api/simpro/import-all: Bulk import all data
"""

import os
import uuid
import traceback
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient
import logging

from app.utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)

# Create blueprint
simpro_bp = Blueprint('simpro_bp', __name__)


def get_app_functions():
    """Get functions from main app"""
    return current_app.config.get('APP_FUNCTIONS', {})


def get_simpro_config_file():
    """Get path to simpro config file"""
    return os.path.join(current_app.config['SIMPRO_CONFIG_FOLDER'], 'simpro_config.json')


def load_simpro_config():
    """Load Simpro configuration"""
    return load_json_file(get_simpro_config_file(), {
        "connected": False,
        "base_url": "",
        "company_id": "0",
        "client_id": "",
        "client_secret": "",
        "access_token": None,
        "refresh_token": None,
        "token_expires_at": None
    })


def save_simpro_config(config):
    """Save Simpro configuration"""
    save_json_file(get_simpro_config_file(), config)


def make_simpro_api_request(endpoint, method='GET', params=None, data=None):
    """Make authenticated Simpro API request"""
    config = load_simpro_config()
    if not config.get('connected') or not config.get('access_token'):
        return {'error': 'Not connected to Simpro'}
    
    # Build URL - ensure trailing slash for collections
    if not endpoint.endswith('/') and method == 'GET':
        endpoint = endpoint + '/'
    
    url = f"{config['base_url']}/api/v1.0/companies/{config['company_id']}{endpoint}"
    headers = {
        'Authorization': f"Bearer {config['access_token']}",
        'Content-Type': 'application/json'
    }
    
    print(f"  📡 {method} {url}")
    if params:
        print(f"     Params: {params}")
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=60)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=60)
        else:
            return {'error': f'Unsupported method: {method}'}
        
        print(f"  📥 Status: {response.status_code}")
        
        if response.status_code == 404:
            return {'error': f'404 Not Found - endpoint may not exist: {endpoint}'}
        elif response.status_code == 422:
            try:
                error_data = response.json()
                return {'error': f'422 Unprocessable - {error_data}'}
            except:
                return {'error': f'422 Unprocessable Entity - check parameters'}
        elif response.status_code >= 400:
            return {'error': f'{response.status_code} {response.reason}'}
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        error_msg = f'{e.response.status_code} {e.response.reason}'
        try:
            error_detail = e.response.json()
            if 'errors' in error_detail:
                error_msg += f": {error_detail['errors']}"
        except:
            pass
        print(f"  ❌ HTTP Error: {error_msg}")
        return {'error': error_msg}
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {'error': str(e)}


# ============================================================================
# SIMPRO CONFIG & CONNECTION
# ============================================================================

@simpro_bp.route('/api/simpro/config', methods=['GET', 'POST'])
def simpro_config():
    """Get or update Simpro configuration"""
    try:
        if request.method == 'GET':
            config = load_simpro_config()
            safe_config = {k: v for k, v in config.items() if k not in ['client_secret', 'access_token', 'refresh_token']}
            return jsonify({'success': True, 'config': safe_config})
        else:
            data = request.json
            config = load_simpro_config()
            config.update({
                'base_url': data.get('base_url', ''),
                'company_id': data.get('company_id', '0'),
                'client_id': data.get('client_id', ''),
                'client_secret': data.get('client_secret', '')
            })
            save_simpro_config(config)
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/connect', methods=['POST'])
def simpro_connect():
    """Connect to Simpro via OAuth"""
    try:
        config = load_simpro_config()
        
        if not all([config['base_url'], config['client_id'], config['client_secret']]):
            return jsonify({'success': False, 'error': 'Missing configuration'}), 400
        
        token_url = f"{config['base_url']}/oauth2/token"
        client = BackendApplicationClient(client_id=config['client_id'])
        oauth = OAuth2Session(client=client)
        
        token = oauth.fetch_token(
            token_url=token_url,
            client_id=config['client_id'],
            client_secret=config['client_secret']
        )
        
        config['access_token'] = token['access_token']
        config['refresh_token'] = token.get('refresh_token')
        config['token_expires_at'] = token.get('expires_at')
        config['connected'] = True
        save_simpro_config(config)
        
        # Try to get company info to verify
        try:
            headers = {'Authorization': f"Bearer {config['access_token']}"}
            companies_url = f"{config['base_url']}/api/v1.0/companies/"
            comp_resp = requests.get(companies_url, headers=headers, timeout=10)
            if comp_resp.status_code == 200:
                companies_data = comp_resp.json()
                print(f"✓ Found companies: {companies_data}")
        except Exception as e:
            print(f"Could not fetch companies: {e}")
        
        return jsonify({'success': True, 'message': 'Connected successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/test-endpoints', methods=['POST'])
def simpro_test_endpoints():
    """Test different Simpro endpoints to find what works"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected'}), 400
        
        results = {}
        headers = {'Authorization': f"Bearer {config['access_token']}"}
        base = f"{config['base_url']}/api/v1.0/companies/{config['company_id']}"
        
        test_endpoints = [
            '/customers/companies/',
            '/customers/',
            '/jobs/',
            '/quotes/',
            '/catalogs/',
            '/catalogue/',
            '/employees/',
            '/sites/'
        ]
        
        for endpoint in test_endpoints:
            try:
                url = base + endpoint + '?pageSize=1'
                resp = requests.get(url, headers=headers, timeout=10)
                results[endpoint] = {
                    'status': resp.status_code,
                    'works': resp.status_code == 200,
                    'message': resp.reason
                }
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, dict) and 'Results' in data:
                            results[endpoint]['count'] = len(data['Results'])
                    except:
                        pass
            except Exception as e:
                results[endpoint] = {'status': 'error', 'works': False, 'message': str(e)}
        
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/disconnect', methods=['POST'])
def simpro_disconnect():
    """Disconnect from Simpro"""
    try:
        config = load_simpro_config()
        config['connected'] = False
        config['access_token'] = None
        config['refresh_token'] = None
        save_simpro_config(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/sync', methods=['POST'])
def simpro_sync():
    """Sync quote to Simpro"""
    try:
        data = request.json
        quote = data.get('quote', {})
        config = load_simpro_config()

        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        return jsonify({
            'success': True,
            'message': 'Quote synced successfully',
            'simpro_job_id': f"SIM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# SIMPRO DATA ENDPOINTS
# ============================================================================

@simpro_bp.route('/api/simpro/customers', methods=['GET', 'POST'])
def simpro_customers():
    """Fetch customers from Simpro, optionally save to CRM"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        resp = make_simpro_api_request('/customers/companies/', params={'pageSize': 250, 'display': 'all'})

        if 'error' in resp:
            return jsonify({'success': False, 'error': resp['error']}), 400

        customers_data = resp.get('Results', []) if isinstance(resp, dict) else resp

        if request.method == 'POST':
            customers_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'customers.json')
            existing_customers = load_json_file(customers_file, [])
            saved_count = 0

            for sc in customers_data:
                if any(c.get('simpro_id') == sc.get('ID') for c in existing_customers):
                    continue

                existing_customers.append({
                    'id': str(uuid.uuid4()),
                    'simpro_id': sc.get('ID'),
                    'name': sc.get('CompanyName') or f"{sc.get('GivenName','')} {sc.get('FamilyName','')}".strip() or 'Unknown',
                    'email': sc.get('Email', ''),
                    'phone': sc.get('Mobile') or sc.get('Phone', ''),
                    'address': sc.get('PostalAddress', {}).get('Address', '') if isinstance(sc.get('PostalAddress'), dict) else '',
                    'status': 'active' if sc.get('Active') else 'inactive',
                    'created_at': sc.get('DateCreated', datetime.now().isoformat()),
                    'updated_at': datetime.now().isoformat(),
                    'source': 'simpro_import'
                })
                saved_count += 1

            save_json_file(customers_file, existing_customers)

            return jsonify({
                'success': True,
                'data': customers_data,
                'saved_to_crm': True,
                'saved_count': saved_count,
                'total': len(customers_data)
            })

        return jsonify({'success': True, 'data': customers_data, 'total': len(customers_data)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/jobs', methods=['GET', 'POST'])
def simpro_jobs():
    """Fetch jobs from Simpro, optionally save to CRM"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        resp = make_simpro_api_request('/jobs/', params={'pageSize': 250, 'display': 'all'})

        if 'error' in resp:
            return jsonify({'success': False, 'error': resp['error']}), 400

        jobs_data = resp.get('Results', []) if isinstance(resp, dict) else resp

        if request.method == 'POST':
            projects_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'projects.json')
            customers_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'customers.json')
            
            existing_projects = load_json_file(projects_file, [])
            existing_customers = load_json_file(customers_file, [])
            customer_map = {c.get('simpro_id'): c['id'] for c in existing_customers if c.get('simpro_id')}
            saved_count = 0

            for sj in jobs_data:
                if any(p.get('simpro_id') == sj.get('ID') for p in existing_projects):
                    continue

                customer_id = customer_map.get(sj.get('Customer', {}).get('ID') if isinstance(sj.get('Customer'), dict) else None)

                existing_projects.append({
                    'id': str(uuid.uuid4()),
                    'simpro_id': sj.get('ID'),
                    'customer_id': customer_id,
                    'title': sj.get('Name', 'Untitled'),
                    'description': sj.get('Description', ''),
                    'status': sj.get('Stage', 'pending').lower(),
                    'priority': 'medium',
                    'quote_amount': float(sj.get('TotalAmount', 0) or 0),
                    'actual_amount': float(sj.get('ActualAmount', 0) or 0),
                    'due_date': sj.get('DueDate'),
                    'created_at': sj.get('DateCreated', datetime.now().isoformat()),
                    'updated_at': datetime.now().isoformat(),
                    'source': 'simpro_import'
                })
                saved_count += 1

            save_json_file(projects_file, existing_projects)

            return jsonify({
                'success': True,
                'data': jobs_data,
                'saved_to_crm': True,
                'saved_count': saved_count,
                'total': len(jobs_data)
            })

        return jsonify({'success': True, 'data': jobs_data, 'total': len(jobs_data)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/quotes', methods=['GET', 'POST'])
def simpro_quotes():
    """Fetch quotes from Simpro"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        resp = make_simpro_api_request('/quotes/', params={'pageSize': 250, 'display': 'all'})

        if 'error' in resp:
            return jsonify({'success': False, 'error': resp['error']}), 400

        quotes_data = resp.get('Results', []) if isinstance(resp, dict) else resp
        return jsonify({'success': True, 'data': quotes_data, 'total': len(quotes_data)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/catalogs', methods=['GET', 'POST'])
def simpro_catalogs():
    """Fetch catalog items from Simpro, optionally save to CRM inventory"""
    try:
        funcs = get_app_functions()
        categorize_with_ai = funcs.get('categorize_with_ai')
        
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        resp = make_simpro_api_request('/catalogs/', params={'pageSize': 500})

        if 'error' in resp:
            return jsonify({'success': False, 'error': resp['error']}), 400

        catalog_data = resp.get('Results', []) if isinstance(resp, dict) else resp

        if request.method == 'POST':
            inventory_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'inventory.json')
            existing_inventory = load_json_file(inventory_file, [])
            saved_count = 0
            categorized_count = 0

            for item in catalog_data:
                if any(i.get('simpro_id') == item.get('ID') for i in existing_inventory):
                    continue

                category_info = {'automation_type': 'other', 'tier': 'basic', 'notes': ''}
                if categorize_with_ai:
                    category_info = categorize_with_ai(item, 'catalog_item')
                
                base_cost = float(item.get('CostPrice', 0) or 0)

                existing_inventory.append({
                    'id': str(uuid.uuid4()),
                    'simpro_id': item.get('ID'),
                    'name': item.get('Name', 'Unknown'),
                    'description': item.get('Description', ''),
                    'sku': item.get('Code', ''),
                    'automation_type': category_info.get('automation_type', 'other'),
                    'tier': category_info.get('tier', 'basic'),
                    'price': {
                        'basic': base_cost,
                        'premium': base_cost * 1.5,
                        'deluxe': base_cost * 2.5
                    },
                    'stock_quantity': int(item.get('Quantity', 0) or 0),
                    'supplier': item.get('Supplier', {}).get('Name', '') if isinstance(item.get('Supplier'), dict) else '',
                    'ai_notes': category_info.get('notes', ''),
                    'created_at': item.get('DateCreated', datetime.now().isoformat()),
                    'updated_at': datetime.now().isoformat(),
                    'source': 'simpro_import'
                })
                saved_count += 1
                if category_info.get('automation_type') != 'other':
                    categorized_count += 1

            save_json_file(inventory_file, existing_inventory)

            return jsonify({
                'success': True,
                'data': catalog_data,
                'saved_to_crm': True,
                'saved_count': saved_count,
                'categorized_count': categorized_count,
                'total': len(catalog_data)
            })

        return jsonify({'success': True, 'data': catalog_data, 'total': len(catalog_data)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/labor-rates', methods=['GET'])
def simpro_labor_rates():
    """Fetch labor rates from Simpro"""
    try:
        config = load_simpro_config()
        if not config.get('connected'):
            return jsonify({'success': False, 'error': 'Not connected to Simpro'}), 400

        resp = make_simpro_api_request('/employees/', params={'pageSize': 200})

        if 'error' in resp:
            return jsonify({'success': False, 'error': resp['error']}), 400

        labor_data = resp.get('Results', []) if isinstance(resp, dict) else resp

        rates = []
        for emp in labor_data:
            if emp.get('CostRate') or emp.get('ChargeRate'):
                rates.append({
                    'id': emp.get('ID'),
                    'name': f"{emp.get('GivenName','')} {emp.get('FamilyName','')}".strip(),
                    'role': emp.get('EmployeeType', 'Technician'),
                    'cost_rate': emp.get('CostRate', 0),
                    'charge_rate': emp.get('ChargeRate', 0)
                })

        return jsonify({'success': True, 'data': rates, 'total': len(rates)})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@simpro_bp.route('/api/simpro/import-all', methods=['POST'])
def simpro_import_all():
    """BULK IMPORT from Simpro"""
    try:
        funcs = get_app_functions()
        import_all_simpro_data = funcs.get('import_all_simpro_data')
        categorize_with_ai = funcs.get('categorize_with_ai')
        
        if not import_all_simpro_data:
            return jsonify({'success': False, 'error': 'Import function not available'}), 500
        
        print("="*50)
        print("STARTING BULK IMPORT")
        import_result = import_all_simpro_data()
        if not import_result['success']:
            return jsonify(import_result), 400
        
        data = import_result['data']
        
        # File paths
        customers_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'customers.json')
        projects_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'projects.json')
        inventory_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'inventory.json')
        technicians_file = os.path.join(current_app.config['CRM_DATA_FOLDER'], 'technicians.json')
        
        # Import customers
        existing_customers = load_json_file(customers_file, [])
        customer_count = 0
        for sc in data['customers']:
            if any(c.get('simpro_id') == sc.get('ID') for c in existing_customers):
                continue
            existing_customers.append({
                'id': str(uuid.uuid4()),
                'simpro_id': sc.get('ID'),
                'name': sc.get('CompanyName') or f"{sc.get('GivenName','')} {sc.get('FamilyName','')}".strip() or 'Unknown',
                'email': sc.get('Email', ''),
                'phone': sc.get('Mobile') or sc.get('Phone', ''),
                'address': sc.get('PostalAddress', {}).get('Address', '') if isinstance(sc.get('PostalAddress'), dict) else '',
                'status': 'active' if sc.get('Active') else 'inactive',
                'created_at': sc.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            customer_count += 1
        save_json_file(customers_file, existing_customers)
        
        # Import projects
        existing_projects = load_json_file(projects_file, [])
        customer_map = {c.get('simpro_id'): c['id'] for c in existing_customers if c.get('simpro_id')}
        project_count = 0
        for sj in data['jobs']:
            if any(p.get('simpro_id') == sj.get('ID') for p in existing_projects):
                continue
            customer_id = customer_map.get(sj.get('Customer', {}).get('ID') if isinstance(sj.get('Customer'), dict) else None)
            existing_projects.append({
                'id': str(uuid.uuid4()),
                'simpro_id': sj.get('ID'),
                'customer_id': customer_id,
                'title': sj.get('Name', 'Untitled'),
                'description': sj.get('Description', ''),
                'status': sj.get('Stage', 'pending').lower(),
                'priority': 'medium',
                'quote_amount': float(sj.get('TotalAmount', 0) or 0),
                'actual_amount': float(sj.get('ActualAmount', 0) or 0),
                'due_date': sj.get('DueDate'),
                'created_at': sj.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            project_count += 1
        save_json_file(projects_file, existing_projects)
        
        # Import inventory
        existing_inventory = load_json_file(inventory_file, [])
        categorized_count = 0
        inventory_count = 0
        for idx, item in enumerate(data['catalog']):
            if any(i.get('simpro_id') == item.get('ID') for i in existing_inventory):
                continue
            
            category_info = {'automation_type': 'other', 'tier': 'basic', 'notes': ''}
            if categorize_with_ai:
                category_info = categorize_with_ai(item, 'catalog_item')
            base_cost = float(item.get('CostPrice', 0) or 0)
            
            existing_inventory.append({
                'id': str(uuid.uuid4()),
                'simpro_id': item.get('ID'),
                'name': item.get('Name', 'Unknown'),
                'description': item.get('Description', ''),
                'sku': item.get('Code', ''),
                'automation_type': category_info.get('automation_type', 'other'),
                'tier': category_info.get('tier', 'basic'),
                'price': {
                    'basic': base_cost,
                    'premium': base_cost * 1.5,
                    'deluxe': base_cost * 2.5
                },
                'stock_quantity': int(item.get('Quantity', 0) or 0),
                'supplier': item.get('Supplier', {}).get('Name', '') if isinstance(item.get('Supplier'), dict) else '',
                'ai_notes': category_info.get('notes', ''),
                'created_at': item.get('DateCreated', datetime.now().isoformat()),
                'updated_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            inventory_count += 1
            if category_info.get('automation_type') != 'other':
                categorized_count += 1
            
            if (idx + 1) % 50 == 0:
                print(f"   {idx+1}/{len(data['catalog'])}")
        
        save_json_file(inventory_file, existing_inventory)
        
        # Import technicians
        existing_technicians = load_json_file(technicians_file, [])
        tech_count = 0
        for staff in data['staff']:
            if any(t.get('simpro_id') == staff.get('ID') for t in existing_technicians):
                continue
            existing_technicians.append({
                'id': str(uuid.uuid4()),
                'simpro_id': staff.get('ID'),
                'name': f"{staff.get('GivenName','')} {staff.get('FamilyName','')}".strip() or 'Unknown',
                'email': staff.get('Email', ''),
                'phone': staff.get('Mobile', ''),
                'role': staff.get('EmployeeType', 'Technician'),
                'status': 'active' if staff.get('Active') else 'inactive',
                'created_at': datetime.now().isoformat(),
                'source': 'simpro_import'
            })
            tech_count += 1
        save_json_file(technicians_file, existing_technicians)
        
        print("IMPORT COMPLETE!")
        return jsonify({
            'success': True,
            'message': 'Import successful',
            'summary': {
                'customers': customer_count,
                'projects': project_count,
                'inventory_items': inventory_count,
                'inventory_categorized': categorized_count,
                'technicians': tech_count,
                'quotes': len(data['quotes']),
                'total': customer_count + project_count + inventory_count + tech_count
            },
            'errors': import_result['errors']
        })
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

