from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo
import os
import json
import re
from datetime import datetime

def extract_sd_metadata(image_path):
    """Stable Diffusion画像からメタデータを抽出"""
    try:
        image = Image.open(image_path)
        metadata = {}

        # PNG info（parameters）を取得
        if hasattr(image, 'text'):
            for key, value in image.text.items():
                if key == 'parameters':
                    metadata = parse_parameters(value)
                    break

        return metadata
    except Exception as e:
        print(f"メタデータ抽出エラー: {e}")
        return {}

def parse_parameters(params_text):
    """parametersテキストを解析してメタデータに変換"""
    try:
        # プロンプトとネガティブプロンプトを分離
        lines = params_text.split('\n')

        metadata = {}

        # プロンプトを取得（最初の行または"Negative prompt:"より前）
        prompt_lines = []
        i = 0
        while i < len(lines) and not lines[i].startswith('Negative prompt:'):
            prompt_lines.append(lines[i])
            i += 1
        metadata['prompt'] = '\n'.join(prompt_lines).strip()

        # ネガティブプロンプトを取得
        if i < len(lines) and lines[i].startswith('Negative prompt:'):
            negative_prompt = lines[i].replace('Negative prompt:', '').strip()
            metadata['negative_prompt'] = negative_prompt
            i += 1

        # 設定パラメータを取得
        if i < len(lines):
            settings_line = lines[i]
            # Steps, CFG scale, Sampler, Seed などを抽出
            settings_pattern = r'(Steps|CFG scale|Sampler|Seed|Size|Model hash|Model): ([^,]+)'
            settings = dict(re.findall(settings_pattern, settings_line))
            metadata.update(settings)

        return metadata
    except Exception as e:
        print(f"パラメータ解析エラー: {e}")
        return {}

def add_watermark(image_path, watermark_path, output_path=None):
    """画像にウォーターマークを追加"""
    try:
        # 元画像を開く
        base_image = Image.open(image_path)

        # ウォーターマークを開く
        watermark = Image.open(watermark_path)

        # ウォーターマークのサイズを調整（200x50に固定）
        watermark = watermark.resize((200, 50), Image.Resampling.LANCZOS)

        # アルファチャンネルがない場合は追加
        if watermark.mode != 'RGBA':
            watermark = watermark.convert('RGBA')

        # 元画像もRGBAに変換
        if base_image.mode != 'RGBA':
            base_image = base_image.convert('RGBA')

        # ウォーターマークの配置位置（右下角から20px離す）
        x = base_image.width - watermark.width - 20
        y = base_image.height - watermark.height - 20

        # ウォーターマークを合成
        base_image.paste(watermark, (x, y), watermark)

        # 出力パスが指定されていない場合は自動生成
        if output_path is None:
            base_name = os.path.splitext(image_path)[0]
            output_path = f"{base_name}_watermarked.png"

        # RGBに変換して保存
        final_image = base_image.convert('RGB')
        final_image.save(output_path, 'PNG')

        return output_path
    except Exception as e:
        print(f"ウォーターマーク追加エラー: {e}")
        return None

def generate_tags(metadata):
    """メタデータから適切なタグを生成"""
    tags = ['#StableDiffusion', '#AI生成', '#綾奈さん']

    # モデル名のタグを追加
    model = metadata.get('Model', '')
    if model:
        # モデル名を整理（拡張子を除去、特殊文字を除去）
        model_clean = model.replace('.safetensors', '').replace('.ckpt', '')
        model_clean = re.sub(r'[^\w\-]', '', model_clean)  # 英数字とハイフン以外を除去
        if model_clean:
            tags.append(f'#{model_clean}')

    # サンプラーのタグを追加
    sampler = metadata.get('Sampler', '')
    if sampler:
        # サンプラー名を整理（スペースをアンダースコアに、特殊文字を除去）
        sampler_clean = sampler.replace(' ', '_').replace('+', 'Plus')
        sampler_clean = re.sub(r'[^\w_]', '', sampler_clean)
        if sampler_clean:
            tags.append(f'#{sampler_clean}')

    return tags

def create_obsidian_note(metadata, image_filename, vault_path, note_name=None, notes_folder="SD_Gallery"):
    """Obsidian用のマークダウンファイルを作成"""
    try:
        # ノート名が指定されていない場合は自動生成
        if note_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            # 画像ファイル名（拡張子なし）を追加
            img_name = os.path.splitext(image_filename)[0]
            note_name = f"SD_Generation_{timestamp}_{img_name}"

        # ノート保存用フォルダを作成（存在しない場合）
        notes_dir = os.path.join(vault_path, notes_folder)
        os.makedirs(notes_dir, exist_ok=True)

        # タグを生成
        tags = generate_tags(metadata)
        tags_string = ' '.join(tags)

        # マークダウン内容を生成
        md_content = f"""# {note_name}

## 基本情報
- 生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 画像ファイル: ![[{image_filename}]]

## プロンプト
```
{metadata.get('prompt', 'N/A')}
```

## ネガティブプロンプト
```
{metadata.get('negative_prompt', 'N/A')}
```

## 生成設定
| パラメータ | 値 |
|------------|-----|
| Steps | {metadata.get('Steps', 'N/A')} |
| CFG Scale | {metadata.get('CFG scale', 'N/A')} |
| Sampler | {metadata.get('Sampler', 'N/A')} |
| Seed | {metadata.get('Seed', 'N/A')} |
| Size | {metadata.get('Size', 'N/A')} |
| Model | {metadata.get('Model', 'N/A')} |
| Model Hash | {metadata.get('Model hash', 'N/A')} |

## タグ
{tags_string}

## メモ
<!-- ここに感想や改善点などを記録 -->

"""

        # ファイルパスを作成
        note_path = os.path.join(notes_dir, f"{note_name}.md")

        # マークダウンファイルを保存
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return note_path
    except Exception as e:
        print(f"Obsidianノート作成エラー: {e}")
        return None

def process_sd_image(image_path, watermark_path, vault_path, obsidian_images_folder="attachments", notes_folder="SD_Gallery"):
    """メイン処理：画像処理からObsidian保存まで一括実行"""
    print(f"処理開始: {image_path}")

    # 1. メタデータ抽出
    print("メタデータを抽出中...")
    metadata = extract_sd_metadata(image_path)

    # 2. ウォーターマーク追加
    print("ウォーターマークを追加中...")
    watermarked_path = add_watermark(image_path, watermark_path)

    if watermarked_path is None:
        print("ウォーターマーク追加に失敗しました")
        return None

    # 3. Obsidianの画像フォルダに移動
    image_filename = os.path.basename(watermarked_path)
    obsidian_image_path = os.path.join(vault_path, obsidian_images_folder, image_filename)

    # 画像フォルダが存在しない場合は作成
    os.makedirs(os.path.dirname(obsidian_image_path), exist_ok=True)

    # 画像をObsidianフォルダにコピー
    import shutil
    shutil.copy2(watermarked_path, obsidian_image_path)

    # 4. Obsidianノート作成
    print("Obsidianノートを作成中...")
    note_path = create_obsidian_note(metadata, image_filename, vault_path, notes_folder=notes_folder)

    print(f"処理完了:")
    print(f"  - 画像: {obsidian_image_path}")
    print(f"  - ノート: {note_path}")

    return {
        'image_path': obsidian_image_path,
        'note_path': note_path,
        'metadata': metadata
    }

def batch_process_images(folder_path, watermark_path, vault_path, obsidian_images_folder="attachments", notes_folder="SD_Gallery"):
    """フォルダ内の全画像ファイルを一括処理"""
    # 対応する画像拡張子
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}

    # フォルダ内の画像ファイルを取得
    image_files = []
    for filename in os.listdir(folder_path):
        if os.path.splitext(filename.lower())[1] in image_extensions:
            image_files.append(os.path.join(folder_path, filename))

    if not image_files:
        print(f"フォルダ内に画像ファイルが見つかりませんでした: {folder_path}")
        return []

    print(f"{len(image_files)}個の画像ファイルを発見しました")

    # 結果を格納するリスト
    results = []
    success_count = 0
    error_count = 0

    # 各画像ファイルを処理
    for i, image_path in enumerate(image_files, 1):
        print(f"\n[{i}/{len(image_files)}] 処理中: {os.path.basename(image_path)}")

        try:
            result = process_sd_image(image_path, watermark_path, vault_path, obsidian_images_folder, notes_folder)
            if result:
                results.append(result)
                success_count += 1
                print(f"✅ 成功: {os.path.basename(image_path)}")
            else:
                error_count += 1
                print(f"❌ 失敗: {os.path.basename(image_path)}")
        except Exception as e:
            error_count += 1
            print(f"❌ エラー ({os.path.basename(image_path)}): {e}")

    # 処理結果の表示
    print(f"\n=== 処理完了 ===")
    print(f"成功: {success_count}件")
    print(f"失敗: {error_count}件")
    print(f"合計: {len(image_files)}件")

    return results

def process_single_or_batch(path, watermark_path, vault_path, obsidian_images_folder="attachments", notes_folder="SD_Gallery"):
    """単一ファイルまたはフォルダを自動判定して処理"""
    if os.path.isfile(path):
        # 単一ファイルの場合
        print("単一ファイルモードで実行")
        return process_sd_image(path, watermark_path, vault_path, obsidian_images_folder, notes_folder)
    elif os.path.isdir(path):
        # フォルダの場合
        print("バッチ処理モードで実行")
        return batch_process_images(path, watermark_path, vault_path, obsidian_images_folder, notes_folder)
    else:
        print(f"指定されたパスが存在しません: {path}")
        return None

# 使用例
if __name__ == "__main__":
    # 設定
    TARGET_PATH = "path/to/your/sd_images"       # 画像ファイルまたはフォルダのパス
    WATERMARK_PATH = "path/to/your/sample.png"  # ウォーターマーク画像のパス
    VAULT_PATH = "path/to/your/myObsidian"     # Obsidian vaultのパス

    # フォルダ設定（カスタマイズ可能）
    IMAGES_FOLDER = "attachments"             # 画像保存フォルダ
    NOTES_FOLDER = "SD_Gallery"               # ノート保存フォルダ

    # 自動判定して処理実行
    result = process_single_or_batch(
        TARGET_PATH,
        WATERMARK_PATH,
        VAULT_PATH,
        obsidian_images_folder=IMAGES_FOLDER,
        notes_folder=NOTES_FOLDER
    )

    if result:
        if isinstance(result, list):
            print(f"バッチ処理が完了しました！{len(result)}件の画像を処理しました。")
        else:
            print("単一ファイルの処理が正常に完了しました！")
    else:
        print("処理中にエラーが発生しました。")
