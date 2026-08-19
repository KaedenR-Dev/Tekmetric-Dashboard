from tekmetric_api import TekmetricAPI

api = TekmetricAPI()

print()
print("Getting employees for Complete Auto Repair...")
print("=" * 70)

params = {
    "shop": api.shop_id,
    "size": 100
}

response = api.get("/employees", params=params)

employees = response.get("content", [])

print()
print(f"Employees returned: {len(employees)}")
print()

for employee in employees:

    employee_id = employee.get("id")

    first_name = employee.get("firstName", "")
    last_name = employee.get("lastName", "")

    role = employee.get("employeeRole") or {}
    role_name = role.get("name", "Unknown")

    print(
        f"ID: {employee_id:<10} "
        f"Name: {first_name} {last_name:<20} "
        f"Role: {role_name}"
    )

print()
print("=" * 70)