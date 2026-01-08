#!/usr/bin/env python3
"""
Genera post Instagram giornaliero: immagine AI + caption
Sincronizzato con articolo blog generato
Pubblica automaticamente su Instagram via Meta Graph API
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
    
    print(f"🎨 Creating image: {output_path}")
    
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
        print("✅ System fonts loaded")
    except Exception as e:
        print(f"⚠️ System fonts not found: {e}, using default")
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
    print(f"✅ Image saved: {output_path}")
    print(f"   Size: {os.path.getsize(output_path) / 1024:.1f} KB")
    return output_path


def generate_caption(topic):
    """Genera caption Instagram via Groq"""
    from groq import Groq
    
    print("📝 Generating caption...")
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY non trovata")
    
    print(f"✅ GROQ_API_KEY found: {api_key[:10]}...")
    
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
    print(f"✅ Caption generated ({len(caption)} chars)")
    print(f"   Preview: {caption[:80]}...")
    return caption


def publish_to_instagram(image_url, caption):
    """Pubblica immagine + caption su Instagram via Meta Graph API usando image_url"""
    
    print("\n=== 📤 Publishing to Instagram ===")
    
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    
    if not access_token:
        print("❌ INSTAGRAM_ACCESS_TOKEN non trovato")
        return False
    
    if not business_account_id:
        print("❌ INSTAGRAM_BUSINESS_ACCOUNT_ID non trovato")
        return False
    
    print(f"✅ TOKEN found: {access_token[:10]}...")
    print(f"✅ ACCOUNT_ID found: {business_account_id}")
    print(f"✅ Image URL: {image_url}")
    
    try:
        # Step 1: Crea media container con image_url (CORRETTO)
        print("📤 Step 1: Creating media container...")
        
        container_url = f"https://graph.instagram.com/v18.0/{business_account_id}/media"
        
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token,
        }
        
        print(f"   POST {container_url}")
        print(f"   Caption length: {len(caption)}")
        
        response = requests.post(container_url, data=payload, timeout=30)
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}")
        
        if response.status_code != 200:
            print(f"❌ Error creating media container: {response.status_code}")
            print(f"   Full response: {response.text}")
            return False
        
        result = response.json()
        
        if 'error' in result:
            print(f"❌ API Error: {result['error']}")
            return False
        
        if 'id' not in result:
            print(f"❌ No media ID in response: {result}")
            return False
        
        media_id = result['id']
        print(f"✅ Media container created: {media_id}")
        
        # Step 2: Pubblica media
        print("📤 Step 2: Publishing media...")
        
        publish_url = f"https://graph.instagram.com/v18.0/{business_account_id}/media_publish"
        
        publish_data = {
            'creation_id': media_id,
            'access_token': access_token
        }
        
        print(f"   POST {publish_url}")
        
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        
        print(f"   Status: {publish_response.status_code}")
        print(f"   Response: {publish_response.text[:300]}")
        
        if publish_response.status_code == 200:
            publish_result = publish_response.json()
            
            if 'id' in publish_result:
                post_id = publish_result['id']
                print(f"🎉 Post published successfully!")
                print(f"   Post ID: {post_id}")
                print(f"   URL: https://instagram.com/p/{post_id}/")
                return True
            else:
                print(f"❌ No post ID in response: {publish_result}")
                return False
        else:
            print(f"❌ Error publishing: {publish_response.status_code}")
            print(f"   Response: {publish_response.text}")
            return False
    
    except requests.exceptions.Timeout:
        print("❌ Request timeout (Instagram API took too long)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error (network issue)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
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
        
        # 2. Crea immagine in docs/instagram/ (GitHub Pages)
        repo_root = Path(__file__).parent.parent
        instagram_dir = repo_root / "docs" / "instagram"
        instagram_dir.mkdir(parents=True, exist_ok=True)
        
        image_filename = f"instagram_post_{now.strftime('%Y%m%d')}.png"
        image_path = instagram_dir / image_filename
        
        generate_image_with_text(
            title="Tech Blog",
            subtitle="Nuovo articolo",
            output_path=str(image_path)
        )
        
        # 3. Crea URL pubblico (GitHub Pages)
        # ⚠️ MODIFICA QUESTO CON IL TUO USERNAME/REPO
        image_url = f"https://serpico3.github.io/Ai-site/instagram/{image_filename}"
        
        print(f"\n📍 Image URL for Instagram: {image_url}")
        
        # 4. Pubblica su Instagram
        success = publish_to_instagram(image_url, caption)
        
        if success:
            print("\n✅ Instagram post published successfully!")
        else:
            print("\n⚠️ Instagram publishing failed")
            print(f"   Image file saved at: {image_path}")
            print(f"   Will be available at: {image_url}")
        
        print("\n" + "=" * 60)
        print(f"✅ GENERATOR COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
