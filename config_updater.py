#!/usr/bin/env python3
"""
Configuration Updater for Lock Zone AI Floor Plan Analyzer
This script helps you easily update prices, descriptions, and settings
"""

import json
import os

CONFIG_FILE = 'data/automation_data.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None

def save_config(config):
    os.makedirs('data', exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Configuration saved to {CONFIG_FILE}")

def update_prices():
    print("\n🏷️  UPDATE PRICING")
    print("=" * 50)
    
    config = load_config()
    if not config:
        print("No config found. Using defaults.")
        return
    
    for key, system in config['automation_types'].items():
        print(f"\n📌 {system['name']}")
        print(f"Current prices:")
        if isinstance(system['base_cost_per_unit'], dict):
            for tier, price in system['base_cost_per_unit'].items():
                print(f"  {tier.upper()}: ${price:.2f}")
        
        update = input(f"Update prices for {system['name']}? (y/n): ").lower()
        if update == 'y':
            try:
                basic = float(input(f"  Basic tier price: $"))
                premium = float(input(f"  Premium tier price: $"))
                deluxe = float(input(f"  Deluxe tier price: $"))
                
                system['base_cost_per_unit'] = {
                    "basic": basic,
                    "premium": premium,
                    "deluxe": deluxe
                }
                print("✅ Prices updated!")
            except ValueError:
                print("❌ Invalid input. Skipping.")
    
    save_config(config)

def update_labor_rates():
    print("\n⏱️  UPDATE LABOR RATES")
    print("=" * 50)
    
    config = load_config()
    if not config:
        return
    
    print(f"Current hourly labor rate: ${config.get('labor_rate', 75):.2f}")
    try:
        new_rate = float(input("New hourly labor rate: $"))
        config['labor_rate'] = new_rate
        print("✅ Labor rate updated!")
        save_config(config)
    except ValueError:
        print("❌ Invalid input.")

def update_markup():
    print("\n💰 UPDATE MARKUP PERCENTAGE")
    print("=" * 50)
    
    config = load_config()
    if not config:
        return
    
    print(f"Current markup: {config.get('markup_percentage', 20)}%")
    try:
        new_markup = float(input("New markup percentage: "))
        config['markup_percentage'] = new_markup
        print("✅ Markup updated!")
        save_config(config)
    except ValueError:
        print("❌ Invalid input.")

def update_company_info():
    print("\n🏢 UPDATE COMPANY INFORMATION")
    print("=" * 50)
    
    config = load_config()
    if not config:
        return
    
    company = config.get('company_info', {})
    
    print(f"Current company name: {company.get('name', 'Lock Zone Automation')}")
    name = input("New company name (or press Enter to keep): ")
    if name:
        company['name'] = name
    
    address = input("Company address (or press Enter to skip): ")
    if address:
        company['address'] = address
    
    phone = input("Company phone (or press Enter to skip): ")
    if phone:
        company['phone'] = phone
    
    email = input("Company email (or press Enter to skip): ")
    if email:
        company['email'] = email
    
    config['company_info'] = company
    print("✅ Company info updated!")
    save_config(config)

def view_config():
    print("\n📋 CURRENT CONFIGURATION")
    print("=" * 50)
    
    config = load_config()
    if not config:
        print("No configuration found.")
        return
    
    print(json.dumps(config, indent=2))

def main():
    print("\n" + "=" * 50)
    print("  🏠 Lock Zone Configuration Manager")
    print("=" * 50)
    
    while True:
        print("\n📝 What would you like to do?")
        print("1. Update automation prices")
        print("2. Update labor rates")
        print("3. Update markup percentage")
        print("4. Update company information")
        print("5. View current configuration")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ")
        
        if choice == '1':
            update_prices()
        elif choice == '2':
            update_labor_rates()
        elif choice == '3':
            update_markup()
        elif choice == '4':
            update_company_info()
        elif choice == '5':
            view_config()
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
