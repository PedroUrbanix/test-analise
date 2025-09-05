from datetime import datetime
now_iso=lambda: datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
log=lambda m: print(f'[{now_iso()}] {m}')
