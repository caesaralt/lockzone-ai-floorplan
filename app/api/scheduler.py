"""
Scheduler Routes Blueprint

Handles background job scheduler:
- /api/scheduler/status: Get scheduler status
- /api/scheduler/run/<job_id>: Manually trigger a job
"""

import logging
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
scheduler_bp = Blueprint('scheduler_bp', __name__)


# ============================================================================
# SCHEDULER API
# ============================================================================

@scheduler_bp.route('/api/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """Get the status of background jobs."""
    try:
        from services.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        return jsonify({
            'success': True,
            'running': scheduler.running,
            'jobs': scheduler.get_job_status()
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@scheduler_bp.route('/api/scheduler/run/<job_id>', methods=['POST'])
def run_scheduler_job(job_id):
    """Manually trigger a scheduled job."""
    try:
        from services.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        if scheduler.run_job_now(job_id):
            return jsonify({'success': True, 'message': f'Job {job_id} executed'})
        return jsonify({'success': False, 'error': 'Job not found'}), 404
        
    except Exception as e:
        logger.error(f"Error running scheduler job: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

