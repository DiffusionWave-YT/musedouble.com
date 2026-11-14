from app.models import AppSetting


def generation_settings(db):
    row = db.get(AppSetting, "generation")
    return row.value if row else {"max_batch": 2, "ratios": ["4:5", "5:4", "1:1", "9:16", "16:9"]}
