from flask import Blueprint, render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from app.models import User
from app.extensions import db

bp = Blueprint('admin', __name__)

@bp.route('/admin/users')
@login_required
def user_management():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
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
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(id)
    user.status = 'approved'
    user.is_approved = True
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/admin/users/<int:id>/reject', methods=['POST'])
@login_required
def reject_user(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    user = User.query.get_or_404(id)
    user.status = 'rejected'
    user.is_approved = False
    db.session.commit()
    
    return jsonify({'success': True})