"""
Functions to sync Staff Admins and Super Users
Add these to your sync scripts
"""

def sync_staff_admins(checkpoint: SyncCheckpoint) -> bool:
    """Sync staff admins from object_5"""
    logging.info("Syncing staff admins...")
    
    try:
        staff_admins = fetch_all_knack_records(OBJECT_KEYS['staff_admins'])
        
        batch = []
        for admin in staff_admins:
            try:
                # Map fields from object_5
                admin_data = {
                    'knack_id': admin['id'],
                    'email': admin.get('field_86', ''),  # Email field
                    'name': admin.get('field_85', '') or admin.get('field_85_raw', '')  # Name field
                }
                
                if admin_data['email']:  # Only sync if email exists
                    batch.append(admin_data)
                
                if len(batch) >= 50:
                    batch_upsert_with_retry('staff_admins', batch, 'knack_id')
                    batch = []
                    
            except Exception as e:
                logging.error(f"Error processing staff admin {admin.get('id')}: {e}")
        
        # Process remaining
        if batch:
            batch_upsert_with_retry('staff_admins', batch, 'knack_id')
        
        logging.info(f"Synced {len(staff_admins)} staff admins")
        return True
        
    except Exception as e:
        logging.error(f"Failed to sync staff admins: {e}")
        return False

def sync_super_users(checkpoint: SyncCheckpoint) -> bool:
    """Sync super users from object_21"""
    logging.info("Syncing super users...")
    
    try:
        super_users = fetch_all_knack_records(OBJECT_KEYS['super_users'])
        
        batch = []
        for user in super_users:
            try:
                # Map fields from object_21
                user_data = {
                    'knack_id': user['id'],
                    'email': user.get('field_86', ''),  # Email field (same as staff admin)
                    'name': user.get('field_85', '') or user.get('field_85_raw', '')  # Name field
                }
                
                if user_data['email']:  # Only sync if email exists
                    batch.append(user_data)
                
                if len(batch) >= 50:
                    batch_upsert_with_retry('super_users', batch, 'knack_id')
                    batch = []
                    
            except Exception as e:
                logging.error(f"Error processing super user {user.get('id')}: {e}")
        
        # Process remaining
        if batch:
            batch_upsert_with_retry('super_users', batch, 'knack_id')
        
        logging.info(f"Synced {len(super_users)} super users")
        return True
        
    except Exception as e:
        logging.error(f"Failed to sync super users: {e}")
        return False