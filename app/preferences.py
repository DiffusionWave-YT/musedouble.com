from app.models import AppSetting


def generation_settings(db):
    row = db.get(AppSetting, "generation")
    return row.value if row else {"max_batch": 2, "ratios": ["1:1", "4:5", "5:4", "3:4", "4:3", "2:3", "3:2", "9:16", "16:9", "21:9"]}
