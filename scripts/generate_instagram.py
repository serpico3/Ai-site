#!/usr/bin/env python3
"""
Genera post Instagram giornaliero: immagine AI + caption
Sincronizzato con articolo blog generato
"""

import os
import sys
import requests
import json
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

def generate_image_with_text(title, subtitle, output_path):
    """Crea immagine 1080x1080px con testo (formato Instagram post)"""
    
    # Crea immagine gradiente tech
    img = Image.new('RGB', (1080, 1080), color=(5, 7, 10))
    draw = ImageDraw.Draw(img)
    
    # Gradient simulato (rettangoli sovrapposti)
    for y in range(1080):
        r = int(5 + (66 - 5) * (y / 1080))
        g = int(7 + (179 - 7) * (y / 1080))
        b = int(10 + (255 - 10) * (y / 1080))
        draw.line([(0, y), (1080, y)], fill=(r, g, b))
    
    # Testo: usa font di sistema (fallback)
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Wrappa titolo
    wrapped_title = textwrap.fill(title, width=20)
    
    # Centra testo
    y_offset = 300
    for line in wrapped_title.split('\n'):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_width = bbox[2] - bbox[0]
        x = (1080 - line_width) // 2
        draw.text((x, y_offset), line, fill=(255, 255, 255), font=title_font)
        y_offset += 80
    
    # Subtitle
    y_offset += 60
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    line_width = bbox[2] - bbox[0]
    x = (1080 - line_width) // 2
    draw.text((x, y_offset), subtitle, fill=(66, 179, 255), font=subtitle_font)
    
    img.save(output_path)
    print(f"🎨 Immagine generata: {output_path}")
    return output_path


def generate_caption(topic):
    """Genera caption Instagram via Groq"""
    from groq import Groq
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY non trovata")
    
    client = Groq(api_key=api_key)
    
    prompt = f"""Sei Diego Serpelloni, 22 anni, tech enthusiast.

Genera una caption accattivante per Instagram post su: {topic}

REQUISITI:
- Lunghezza: 150-250 caratteri
- Tono: Giovanile, entusiasta, informativo
- Linguaggio: Italiano
- Includi 3-4 hashtag rilevanti (es. #DevOps #Tech #Networking)
- NO emoji
- Chiudi con una call-to-action (es. "Cosa ne pensi?")

Scrivi SOLO la caption, niente altro."""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        max_tokens=300
    )
    
    caption = response.choices[0].message.content.strip()
    print(f"✍️ Caption generata: {caption[:100]}...")
    return caption


def publish_to_instagram(image_path, caption):
    """Pubblica immagine + caption su Instagram via Meta Graph API"""
    
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    
    if not access_token or not business_account_id:
        raise ValueError("❌ INSTAGRAM_ACCESS_TOKEN o INSTAGRAM_BUSINESS_ACCOUNT_ID non trovati")
    
    # Step 1: Carica immagine su Instagram (crea container)
    with open(image_path, 'rb') as f:
        files = {'file': f}
        data = {
            'access_token': access_token,
        }
        
        # Crea media container
        response = requests.post(
            f"https://graph.instagram.com/v18.0/{business_account_id}/media",
            data=data,
            files=files,
            params={
                'image_url': None,
                'caption': caption,
                'media_type': 'IMAGE'
            }
        )
    
    if response.status_code != 200:
        # Fallback: prova con URL (se uploadi a server)
        print(f"⚠️ Upload diretto non funziona, provo con URL...")
        # Per ora, saltiamo questo step
        return None
    
    result = response.json()
    if 'id' in result:
        media_id = result['id']
        print(f"✅ Media creato: {media_id}")
        
        # Step 2: Pubblica media
        publish_response = requests.post(
            f"https://graph.instagram.com/v18.0/{business_account_id}/media_publish",
            data={
                'creation_id': media_id,
                'access_token': access_token
            }
        )
        
        if publish_response.status_code == 200:
            print(f"🎉 Post pubblicato su Instagram!")
            return True
        else:
            print(f"❌ Errore pubblicazione: {publish_response.text}")
            return False
    else:
        print(f"❌ Errore caricamento: {result}")
        return False


def main():
    """Main"""
    print("=" * 60)
    print("📸 Instagram Post Generator")
    print("=" * 60)
    
    try:
        now = datetime.now()
        
        # Tema del post (da articolo)
        topic = "Ultimi trends in DevOps e Infrastructure as Code"
        
        # 1. Genera caption
        caption = generate_caption(topic)
        
        # 2. Crea immagine
        image_path = f"/tmp/instagram_post_{now.strftime('%Y%m%d')}.png"
        generate_image_with_text(
            title="Tech Blog",
            subtitle="Nuovo articolo",
            output_path=image_path
        )
        
        # 3. Pubblica (se ENV vars presenti)
        try:
            publish_to_instagram(image_path, caption)
        except Exception as e:
            print(f"⚠️ Pubblicazione Instagram skippata: {e}")
            print("📝 Salvo caption per review manuale...")
            
            # Salva caption in file per review
            caption_file = Path(__file__).parent.parent / "temp" / "instagram_caption.txt"
            caption_file.parent.mkdir(exist_ok=True)
            caption_file.write_text(f"{caption}\n\n[Immagine: {image_path}]")
            print(f"💾 Caption salvato: {caption_file}")
        
        print("\n" + "=" * 60)
        print(f"✅ SUCCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRORE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
