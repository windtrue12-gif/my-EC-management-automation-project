import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

print("🌐 EC一元管理：クラウド（スプレッドシート）自動連動システムを起動します...")

# -------------------------------------------------------------
# 1. Google Sheets API の認証設定
# -------------------------------------------------------------
scope = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
# フォルダに置いた credentials.json を使ってログイン
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
gc = gspread.authorize(creds)

# ふうちゃんが作ったスプレッドシートを開く
# ※もし名前を別にした場合は、ここを実際のスプレッドシート名に変えてね！
spreadsheet_name = "EC一元管理テスト"
sh = gc.open(spreadsheet_name)
print(f"🔓 スプレッドシート「{spreadsheet_name}」へのアクセスに成功しました！")

# -------------------------------------------------------------
# 2. 新しい注文が発生したと仮定する（Yahoo!でITEM-001が2個売れた！）
# -------------------------------------------------------------
new_order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-99"
target_mall = "Yahoo!ショッピング"
target_sku = "ITEM-001"
order_qty = 2

print(f"\n📢 クラウド連携テスト：注文を検知！ [{target_mall}] SKU: {target_sku} / 数量: {order_qty}")

# -------------------------------------------------------------
# 3. 各シートからデータを読み込んで Pandas の DataFrame に変換
# -------------------------------------------------------------
def get_df_from_sheet(sheet_name):
    worksheet = sh.worksheet(sheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data), worksheet

df_products, ws_products = get_df_from_sheet("product_master")
df_inventory, ws_inventory = get_df_from_sheet("inventory_status")
df_orders, ws_orders = get_df_from_sheet("order_management")
df_sales, ws_sales = get_df_from_sheet("sales_summary")

print("📥 クラウドから最新の4つのデータを読み込みました。")

# -------------------------------------------------------------
# 4. 在庫連動ロジック（メモリ上での引き算）
# -------------------------------------------------------------
# 商品マスタ・在庫管理の引き算
df_products.loc[df_products["商品コード"] == target_sku, "在庫数"] -= order_qty
df_inventory.loc[df_inventory["商品コード"] == target_sku, "物理在庫合計"] -= order_qty
df_inventory.loc[df_inventory["商品コード"] == target_sku, "Yahoo在庫"] -= order_qty
print("📉 クラウド上の在庫引き算の計算を完了しました。")

# -------------------------------------------------------------
# 5. 注文履歴の追記ロジック（メモリ上での追加）
# -------------------------------------------------------------
unit_price = int(df_products.loc[df_products["商品コード"] == target_sku, "販売価格"].values[0])
total_price = unit_price * order_qty

new_order_row = {
    "注文ID": new_order_id,
    "注文日時": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "購入モール": target_mall,
    "商品コード": target_sku,
    "数量": order_qty,
    "合計金額": total_price,
    "ステータス": "出荷待ち"
}
df_orders = pd.concat([df_orders, pd.DataFrame([new_order_row])], ignore_index=True)

# -------------------------------------------------------------
# 6. 売上集計の更新ロジック（メモリ上での更新）
# -------------------------------------------------------------
cost_price = int(df_products.loc[df_products["商品コード"] == target_sku, "原価"].values[0])
profit = (unit_price - cost_price) * order_qty
today_str = datetime.now().strftime("%Y-%m-%d")

sales_match = (df_sales["集計日"] == today_str) & (df_sales["購入モール"] == target_mall)

if sales_match.any():
    df_sales.loc[sales_match, "売上金額"] += total_price
    df_sales.loc[sales_match, "注文数"] += 1
    df_sales.loc[sales_match, "粗利"] += profit
else:
    new_sales_row = {
        "集計日": today_str,
        "購入モール": target_mall,
        "売上金額": total_price,
        "注文数": 1,
        "粗利": profit
    }
    df_sales = pd.concat([df_sales, pd.DataFrame([new_sales_row])], ignore_index=True)

# -------------------------------------------------------------
# 7. 更新したデータをGoogleスプレッドシートへ上書き保存（反映）
# -------------------------------------------------------------
def save_df_to_sheet(df, worksheet):
    # スプレッドシートに書き込める形式（リストのリスト）に変換
    # ヘッダー（列名）と中身を合体させる
    all_values = [df.columns.values.tolist()] + df.values.tolist()
    
    # 一旦シートを空っぽにしてから、新しいデータを一発で書き込む
    worksheet.clear()
    worksheet.update(range_name='A1', values=all_values)

save_df_to_sheet(df_products, ws_products)
save_df_to_sheet(df_inventory, ws_inventory)
save_df_to_sheet(df_orders, ws_orders)
save_df_to_sheet(df_sales, ws_sales)

print("\n☁️ すべてのデータがGoogleスプレッドシートに同期されました！完了やよ！")