# app/routes.py
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Category, Product, InventoryTransaction, Invoice, InvoiceItem, User
from datetime import datetime, timedelta
from sqlalchemy import func
import pandas as pd
from io import BytesIO
bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    total_products = Product.query.count()
    total_categories = Category.query.count()
    low_stock_count = Product.query.filter(Product.stock_quantity < 10).count()
    total_transactions = InventoryTransaction.query.count()
    
    recent_products = Product.query.order_by(Product.id.desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.stock_quantity < 10).all()

    return render_template('index.html',
                         total_products=total_products,
                         total_categories=total_categories,
                         low_stock_count=low_stock_count,
                         total_transactions=total_transactions,
                         recent_products=recent_products,
                         low_stock_products=low_stock_products)

@bp.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Access denied. Admin rights required.', 'error')
        return redirect(url_for('main.index'))
    
    # Get users by status
    pending_users = User.query.filter_by(status='pending').all()
    approved_users = User.query.filter_by(status='approved').all()
    rejected_users = User.query.filter_by(status='rejected').all()
    
    return render_template('admin/users.html', 
                         pending_users=pending_users,
                         approved_users=approved_users,
                         rejected_users=rejected_users)

@bp.route('/admin/users/<int:id>/approve', methods=['POST'])
@login_required
def approve_user(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    user = User.query.get_or_404(id)
    user.status = 'approved'
    db.session.commit()
    
    flash(f'User {user.username} has been approved', 'success')
    return jsonify({'success': True})

@bp.route('/admin/users/<int:id>/reject', methods=['POST'])
@login_required
def reject_user(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    user = User.query.get_or_404(id)
    user.status = 'rejected'
    db.session.commit()
    
    flash(f'User {user.username} has been rejected', 'error')
    return jsonify({'success': True})

@bp.route('/products')
@login_required
def product_list():
    products = Product.query.all()
    return render_template('products/list.html', products=products)

@bp.route('/products/create', methods=['GET', 'POST'])
def product_create():
    if request.method == 'POST':
        product = Product(
            name=request.form['name'],
            description=request.form['description'],
            price=float(request.form['price']),
            stock_quantity=int(request.form['stock_quantity']),
            category_id=int(request.form['category_id'])
        )
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('main.product_list'))
    
    categories = Category.query.all()
    return render_template('products/create.html', categories=categories)

@bp.route('/products/edit/<int:id>', methods=['GET', 'POST'])
def product_edit(id):
    product = Product.query.get_or_404(id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.description = request.form['description']
            product.price = float(request.form['price'])
            product.category_id = int(request.form['category_id'])
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('main.product_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'error')
            
    return render_template('products/edit.html', product=product, categories=categories)

@bp.route('/stock/quick-add/<int:id>', methods=['POST'])
@login_required
def quick_add_stock(id):
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 0))
        
        if quantity <= 0:
            return jsonify({
                'success': False,
                'message': 'Quantity must be greater than 0'
            }), 400

        product = Product.query.get_or_404(id)
        
        # Create transaction record
        transaction = InventoryTransaction(
            product_id=product.id,
            quantity=quantity,
            transaction_type='add'
        )
        
        # Update product stock
        product.stock_quantity += quantity
        
        db.session.add(transaction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'new_stock': product.stock_quantity,
            'message': f'Successfully added {quantity} units to stock'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/products/<int:id>/delete', methods=['POST'])
def product_delete(id):
    try:
        product = Product.query.get_or_404(id)
        
        # Check if product has transactions
        if product.transactions:
            return jsonify({
                'success': False,
                'message': 'Cannot delete product with existing transactions'
            }), 400
            
        # Check if product is in any invoices
        if product.invoice_items:
            return jsonify({
                'success': False,
                'message': 'Cannot delete product with existing invoices'
            }), 400
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@bp.route('/categories')
@login_required
def category_list():
    categories = Category.query.all()
    return render_template('categories/list.html', categories=categories)

@bp.route('/categories/create', methods=['GET', 'POST'])
def category_create():
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            category = Category(name=name)
            db.session.add(category)
            try:
                db.session.commit()
                return redirect(url_for('main.category_list'))
            except:
                db.session.rollback()
                return "An error occurred while creating the category.", 500
    return render_template('categories/create.html')

@bp.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
def category_edit(id):
    category = Category.query.get_or_404(id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        if name:
            try:
                category.name = name
                db.session.commit()
                return redirect(url_for('main.category_list'))
            except:
                db.session.rollback()
    
    return render_template('categories/edit.html', category=category)

@bp.route('/categories/delete/<int:id>', methods=['POST'])
def category_delete(id):
    category = Category.query.get_or_404(id)
    try:
        db.session.delete(category)
        db.session.commit()
        return jsonify({"success": True, "message": "Category deleted successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    
@bp.route('/transactions')
@login_required
def transaction_list():
    transactions = InventoryTransaction.query.order_by(InventoryTransaction.timestamp.desc()).all()
    return render_template('transactions/list.html', transactions=transactions)

@bp.route('/transactions/create', methods=['GET', 'POST'])
def transaction_create():
    if request.method == 'POST':
        try:
            product_id = request.form.get('product_id')
            quantity = int(request.form.get('quantity'))
            transaction_type = request.form.get('transaction_type')
            
            product = Product.query.get_or_404(product_id)
            
            # Validate stock for removal
            if transaction_type == 'remove' and product.stock_quantity < quantity:
                return jsonify({
                    'success': False,
                    'message': 'Error: Not enough stock available'
                }), 400

            # Create transaction
            transaction = InventoryTransaction(
                product_id=product_id,
                quantity=quantity,
                transaction_type=transaction_type,
                timestamp=datetime.now()
            )
            
            # Update product stock
            if transaction_type == 'add':
                product.stock_quantity += quantity
            else:
                product.stock_quantity -= quantity

            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Transaction recorded successfully! New stock level for {product.name}: {product.stock_quantity}',
                'new_stock': product.stock_quantity
            })
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error: {str(e)}'
            }), 500
            
    products = Product.query.all()
    return render_template('transactions/create.html', products=products)

@bp.route('/transactions/<int:id>/delete', methods=['POST'])
def transaction_delete(id):
    try:
        transaction = InventoryTransaction.query.get_or_404(id)
        product = transaction.product

        # Reverse the transaction effect on stock
        if transaction.transaction_type == 'add':
            if product.stock_quantity < transaction.quantity:
                return jsonify({
                    'success': False,
                    'message': f'Cannot delete: Would result in negative stock for {product.name}'
                }), 400
            product.stock_quantity -= transaction.quantity
        else:  # transaction_type == 'remove'
            product.stock_quantity += transaction.quantity

        db.session.delete(transaction)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Transaction deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/invoices')
@login_required
def invoice_list():
    try:
        invoices = Invoice.query.order_by(Invoice.date.desc()).all()
        return render_template('invoices/list.html', invoices=invoices)
    except Exception as e:
        print(f"Error: {str(e)}")  # For debugging
        flash('An error occurred while loading invoices', 'error')
        return redirect(url_for('main.index'))

@bp.route('/invoices/create', methods=['GET', 'POST'])
def invoice_create():
    if request.method == 'POST':
        try:
            # Print the received data for debugging
            print("Received data:", request.get_json())
            data = request.get_json()
            
            # Generate invoice number
            invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{Invoice.query.count() + 1:04d}"
            
            # Print each step for debugging
            print("Creating invoice with number:", invoice_number)
            invoice = Invoice(
                invoice_number=invoice_number,
                customer_name=data['customer_name'],
                customer_email=data.get('customer_email'),
                customer_address=data.get('customer_address'),
                total_amount=data['total_amount'],
                status='pending'
            )
            
            print("Processing invoice items...")
            # Add invoice items
            for item in data['items']:
                print(f"Processing item: {item}")
                product = Product.query.get(item['product_id'])
                if not product:
                    raise ValueError(f"Product with ID {item['product_id']} not found")
                
                invoice_item = InvoiceItem(
                    product_id=item['product_id'],
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    subtotal=item['quantity'] * item['unit_price']
                )
                invoice.items.append(invoice_item)
                
                if product.stock_quantity < item['quantity']:
                    return jsonify({
                        'success': False,
                        'message': f'Insufficient stock for {product.name}'
                    }), 400
                
                product.stock_quantity -= item['quantity']
                
                transaction = InventoryTransaction(
                    product_id=product.id,
                    quantity=item['quantity'],
                    transaction_type='remove'
                )
                db.session.add(transaction)
            
            print("Adding to database...")
            db.session.add(invoice)
            db.session.commit()
            print("Database commit successful!")
            
            return jsonify({
                'success': True,
                'invoice_id': invoice.id,
                'message': 'Invoice created successfully'
            })
            
        except Exception as e:
            db.session.rollback()
            print("Error occurred:", str(e))
            print("Error type:", type(e))
            import traceback
            print("Traceback:", traceback.format_exc())
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    products = Product.query.filter(Product.stock_quantity > 0).all()
    return render_template('invoices/create.html', products=products)

@bp.route('/invoices/<int:id>')
def invoice_view(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoices/view.html', invoice=invoice)

@bp.route('/invoices/<int:id>/mark-paid', methods=['POST'])
def invoice_mark_paid(id):
    try:
        invoice = Invoice.query.get_or_404(id)
        invoice.status = 'paid'
        db.session.commit()
        flash('Invoice marked as paid successfully!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    
@bp.route('/invoices/<int:id>/delete', methods=['POST'])
def invoice_delete(id):
    try:
        invoice = Invoice.query.get_or_404(id)
        
        # Restore product quantities before deleting
        for item in invoice.items:
            product = item.product
            product.stock_quantity += item.quantity
            
            # Add a transaction record for the restoration
            transaction = InventoryTransaction(
                product_id=product.id,
                quantity=item.quantity,
                transaction_type='add'
            )
            db.session.add(transaction)
        
        db.session.delete(invoice)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Invoice deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/analytics')
@login_required
def analytics():
    try:
        # Get date range from request parameters
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Convert string dates to datetime
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include full end date
        
        # Daily transactions with date filter
        daily_transactions = db.session.query(
            func.date(InventoryTransaction.timestamp).label('date'),
            func.count().label('count')
        ).filter(
            InventoryTransaction.timestamp.between(start_datetime, end_datetime)
        ).group_by(func.date(InventoryTransaction.timestamp))\
        .all()

        # Monthly sales with date filter
        monthly_sales = db.session.query(
            func.DATE_FORMAT(Invoice.date, '%Y-%m').label('month'),
            func.sum(Invoice.total_amount).label('total_sales')
        ).filter(
            Invoice.status == 'paid',
            Invoice.date.between(start_datetime, end_datetime)
        ).group_by('month')\
        .order_by('month')\
        .all()

        # Add stock by category query
        stock_by_category = db.session.query(
            Category.name,
            func.sum(Product.stock_quantity).label('total_stock')
        ).join(Product)\
        .group_by(Category.name)\
        .all()

        category_labels = [item.name for item in stock_by_category]
        category_stock = [float(item.total_stock or 0) for item in stock_by_category]

        return render_template('analytics/dashboard.html',
                             start_date=start_date,
                             end_date=end_date,
                             transaction_dates=[t.date.strftime('%Y-%m-%d') for t in daily_transactions],
                             transaction_counts=[t.count for t in daily_transactions],
                             monthly_sales_labels=[m.month for m in monthly_sales],
                             monthly_sales_data=[float(m.total_sales or 0) for m in monthly_sales],
                             category_labels=category_labels,
                             category_stock=category_stock)

    except Exception as e:
        print(f"Error in analytics: {str(e)}")
        flash('Error loading analytics data', 'error')
        return redirect(url_for('main.index'))

@bp.route('/analytics/export')
@login_required
def analytics_export():
    try:
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)

        # Prepare data for export with date filter
        products_data = []
        products = Product.query.all()
        for product in products:
            products_data.append({
                'ID': product.id,
                'Name': product.name,
                'Category': product.category.name,
                'Description': product.description,
                'Price': product.price,
                'Stock': product.stock_quantity
            })
        
        transactions_data = []
        transactions = InventoryTransaction.query.filter(
            InventoryTransaction.timestamp.between(start_datetime, end_datetime)
        ).all()
        for transaction in transactions:
            transactions_data.append({
                'ID': transaction.id,
                'Product': transaction.product.name,
                'Type': transaction.transaction_type,
                'Quantity': transaction.quantity,
                'Date': transaction.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

        # Create Excel file
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Products sheet
            pd.DataFrame(products_data).to_excel(writer, sheet_name='Products', index=False)
            
            # Transactions sheet
            pd.DataFrame(transactions_data).to_excel(writer, sheet_name='Transactions', index=False)
            
            workbook = writer.book
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4e73df',
                'font_color': 'white',
                'border': 1
            })
            
            # Auto-adjust columns width
            for sheet in writer.sheets.values():
                for idx, col in enumerate(pd.DataFrame(products_data).columns):
                    series = pd.DataFrame(products_data)[col]
                    max_len = max((
                        series.astype(str).map(len).max(),
                        len(str(col))
                    )) + 2
                    sheet.set_column(idx, idx, max_len)
                
                # Set header format
                for col_num, value in enumerate(pd.DataFrame(products_data).columns.values):
                    sheet.write(0, col_num, value, header_format)

        # Prepare the file for download
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'inventory_report_{start_date}_to_{end_date}.xlsx'
        )
    

    except Exception as e:
        print(f"Export error: {str(e)}")
        flash('Error exporting report', 'error')
        return redirect(url_for('main.analytics'))