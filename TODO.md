# TODO for Assembler Dashboard - Auto Create OrderDetails

- [x] Run python manage.py migrate (to apply existing migrations)
- [x] Modify accounts/views.py: Import OrderDetails, update assembly_engineer_dashboard to create OrderDetails after saving MainActuator
- [x] Update assembler_dashboard view in accounts/views.py to fetch and display OrderDetails
- [x] Update accounts/templates/accounts/assembler_dashboard.html to display list of OrderDetails
- [x] Test the functionality by running server and simulating save
