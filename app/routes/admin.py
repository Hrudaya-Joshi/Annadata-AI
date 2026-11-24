from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import (
    User, Restaurant, NGO, Volunteer, FoodDonation,
    DonationRequest, PickupAssignment, RescueMission,
    AgentExecutionLog, AuditLog, ImpactRecord
)
from app.services.emergency_service import EmergencyRescueService
from app.services.impact_service import ImpactAnalyticsService

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required():
    if not current_user.is_authenticated or current_user.role != 'admin':
        flash('Administrator access required.', 'danger')
        return False
    return True


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not admin_required():
        return redirect(url_for('main.home'))

    # Platform overview metrics
    total_users = User.query.count()
    restaurants_count = Restaurant.query.count()
    ngos_count = NGO.query.count()
    volunteers_count = Volunteer.query.count()
    total_donations = FoodDonation.query.count()

    active_missions = RescueMission.query.filter(
        RescueMission.status.notin_(['completed', 'cancelled'])
    ).all()
    completed_missions_count = RescueMission.query.filter(
        RescueMission.status.in_(['delivery_confirmed', 'completed'])
    ).count()

    emergencies = EmergencyRescueService.scan_and_escalate(threshold_hours=2.0)

    # Agent execution stats & failures
    agent_logs = AgentExecutionLog.query.order_by(AgentExecutionLog.created_at.desc()).limit(15).all()
    agent_failures = AgentExecutionLog.query.filter_by(status='failed').count()

    # Recent Audit Logs
    audit_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(15).all()

    # Safety flags
    flagged_donations = FoodDonation.query.filter_by(status='unsuitable').all()

    stats = {
        'total_users': total_users,
        'restaurants': restaurants_count,
        'ngos': ngos_count,
        'volunteers': volunteers_count,
        'total_donations': total_donations,
        'pending_analysis': FoodDonation.query.filter_by(status='pending_analysis').count(),
        'suitable_donations': FoodDonation.query.filter_by(status='suitable').count(),
        'unsuitable_donations': len(flagged_donations),
        'active_missions': len(active_missions),
        'completed_missions': completed_missions_count,
        'agent_failures': agent_failures,
        'emergency_count': len(emergencies)
    }

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        active_missions=active_missions,
        emergencies=emergencies,
        agent_logs=agent_logs,
        audit_logs=audit_logs,
        flagged_donations=flagged_donations
    )


@admin_bp.route('/users')
@login_required
def users():
    if not admin_required():
        return redirect(url_for('main.home'))

    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if not admin_required():
        return redirect(url_for('main.home'))

    target_user = User.query.get_or_404(user_id)
    if target_user.id == current_user.id:
        flash('Cannot deactivate your own administrator account.', 'warning')
        return redirect(url_for('admin.users'))

    target_user.is_active = not target_user.is_active
    audit = AuditLog(
        user_id=current_user.id,
        action="TOGGLE_USER_STATUS",
        target_type="User",
        target_id=target_user.id,
        details=f"Admin set user {target_user.email} active={target_user.is_active}"
    )
    db.session.add(audit)
    db.session.commit()

    flash(f"User {target_user.email} status updated to {'Active' if target_user.is_active else 'Deactivated'}.", 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/donations')
@login_required
def donations():
    if not admin_required():
        return redirect(url_for('main.home'))

    all_donations = FoodDonation.query.order_by(FoodDonation.created_at.desc()).all()
    return render_template('admin/donations.html', donations=all_donations)


@admin_bp.route('/agent-logs')
@login_required
def agent_logs():
    if not admin_required():
        return redirect(url_for('main.home'))

    logs = AgentExecutionLog.query.order_by(AgentExecutionLog.created_at.desc()).limit(100).all()
    return render_template('admin/agent_logs.html', logs=logs)


@admin_bp.route('/audit-logs')
@login_required
def audit_logs():
    if not admin_required():
        return redirect(url_for('main.home'))

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()
    return render_template('admin/audit_logs.html', logs=logs)
