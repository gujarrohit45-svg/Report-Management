# TODO for Assembler Dashboard Layout Change

## Tasks
- [x] Update `accounts/views.py` to fetch MainActuator with annotations for completed_qty and pending_qty, handle selected order, and process POST requests for saving/updating OrderDetails.
- [x] Update `accounts/templates/accounts/assembler_dashboard.html` to display first table with order details and second table for selected order's OrderDetails with editable fields and action buttons.
- [ ] Test the dashboard: Load first table, verify calculations, click order_no to show second table, edit and save heat_no fields, submit to change status.
- [ ] Ensure no errors in console and data persists correctly.

## Progress
- Updated `accounts/views.py` to fetch MainActuator with annotations and handle POST requests.
