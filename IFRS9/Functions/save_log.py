from ..models import Log

def save_log(function_name, log_level, message, status='SUCCESS'):
    """
    Function to save logs to the Log table.

    """
    try:
        log_entry = Log(
            function_name=function_name,
            log_level=log_level,
            message=message,
            status=status
        )
        log_entry.save()
        print(f"Log saved: {function_name} - {log_level} - {status}")
    except Exception as e:
        print(f"Failed to save log: {e}")
