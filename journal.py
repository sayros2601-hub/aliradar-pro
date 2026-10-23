"""Build multilingual editorial pages and a separate, stable article-only RSS."""
from datetime import datetime
from email.utils import format_datetime
from html import escape as esc
import xml.etree.ElementTree as ET
from dealvault_core import LANGUAGES, page_path, public_path
from journal_content import ARTICLES, COPY, PROFILE, PUBLISHED

def article_path(lang, slug):
    return page_path(lang, legal='journal/'+slug)

def feed_path(lang):
    return 'journal/rss.xml' if lang == 'en' else lang+'/journal/rss.xml'

def navigation(lang):
    c = COPY[lang]
    return (f'<a href="{public_path(page_path(lang,legal="journal/index"))}">{esc(c["title"])}</a>'
            f'<a href="{public_path(page_path(lang,legal="about"))}">{esc(c["about"])}</a>'
            f'<a href="{PROFILE}" rel="noopener">Flipboard</a>'
            '<a href="https://www.pinterest.com/dealvault_finds/" rel="noopener">Pinterest</a>')

def teaser(lang):
    c = COPY[lang]
    links = ''.join(f'<li><a href="{public_path(article_path(lang,a["slug"]))}">{esc(a["translations"][lang][0])}</a></li>' for a in ARTICLES)
    return f'<section class="wrap prose journal-teaser"><h2>{esc(c["title"])}</h2><p>{esc(c["intro"])}</p><ul>{links}</ul></section>'

def build_journal(builder):
    author = {'@type':'Organization','name':'DealVault','url':builder.domain+'/', 'sameAs':[PROFILE,'https://www.pinterest.com/dealvault_finds/']}
    email = builder.db['site_meta'].get('contact_email')
    for lang in LANGUAGES:
        c = COPY[lang]
        root = ET.Element('rss', version='2.0')
        channel = ET.SubElement(root,'channel')
        for tag,value in [('title',c['title']),('link',builder.domain+public_path(page_path(lang,legal='journal/index'))),('description',c['intro']),('language',lang)]:
            ET.SubElement(channel,tag).text=value
        cards=[]
        for a in ARTICLES:
            title,*sections = a['translations'][lang]
            product = next(p for p in builder.products if p['id']==a['image_id'])
            image=builder.images[product['image']]
            current=article_path(lang,a['slug'])
            url=builder.domain+public_path(current)
            content=''.join(f'<section><h2>{esc(heading)}</h2><p>{esc(text)}</p></section>' for heading,text in sections)
            if a.get('source'):
                label,source=a['source']
                content+=f'<p><a href="{esc(source)}" rel="noopener">{esc(label)}</a></p>'
            body=(f'<main id="main" class="wrap prose journal-article"><article><p class="eyebrow">DEALVAULT / JOURNAL</p><h1>{esc(title)}</h1>'
                  f'<p>DealVault · <time datetime="{PUBLISHED}">2026-10-23</time></p><p class="journal-notice">{esc(c["notice"])}</p>'
                  f'<img class="journal-cover" src="/{image}" alt="{esc(title)}" width="800" height="800">{content}</article>'
                  f'<p><a href="{public_path(page_path(lang))}">{esc(c["read"])}</a> · <a href="{PROFILE}">{esc(c["follow"])}</a></p></main>')
            schema={'@context':'https://schema.org','@type':'Article','headline':title,'description':sections[0][1], 'image':builder.domain+'/'+image,
                    'datePublished':PUBLISHED,'dateModified':PUBLISHED,'author':author,'publisher':author,'url':url,'mainEntityOfPage':url,'inLanguage':lang}
            builder.write(current,builder.shell(lang,current,title,body,legal='journal/'+a['slug'],schemas=schema,social_image=image,summary=sections[0][1],article=True))
            cards.append(f'<article><a href="{public_path(current)}"><img class="journal-thumb" src="/{image}" alt="{esc(title)}" width="800" height="800" loading="lazy"><h2>{esc(title)}</h2></a><p>{esc(sections[0][1])}</p></article>')
            item=ET.SubElement(channel,'item')
            for tag,value in [('title',title),('link',url),('description',c['notice']+' '+ ' '.join(text for _,text in sections)),('pubDate',format_datetime(datetime.fromisoformat(PUBLISHED))),('{http://purl.org/dc/elements/1.1/}creator','DealVault')]:
                ET.SubElement(item,tag).text=value
            ET.SubElement(item,'guid',isPermaLink='true').text=url
            ET.SubElement(item,'enclosure',url=builder.domain+'/'+image,type='image/webp',length=str((builder.out/image).stat().st_size))
        builder.write(feed_path(lang),'<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(root,encoding='unicode'))
        current=page_path(lang,legal='journal/index')
        body=f'<main id="main" class="wrap prose"><p class="eyebrow">DEALVAULT</p><h1>{esc(c["title"])}</h1><p>{esc(c["intro"])}</p><p><a href="/{feed_path(lang)}">{esc(c["rss"])}</a> · <a href="{PROFILE}">Flipboard</a></p><div class="journal-grid">'+''.join(cards)+'</div></main>'
        builder.write(current,builder.shell(lang,current,c['title'],body,legal='journal/index',summary=c['intro']))
        current=page_path(lang,legal='about')
        contact=f'<p>{esc(c["contact"])} <a href="mailto:{esc(email)}">{esc(email)}</a></p>' if email else ''
        body=f'<main id="main" class="wrap prose"><h1>{esc(c["about"])}</h1><p>{esc(c["about_text"])}</p>{contact}<p><a href="{PROFILE}">Flipboard</a> · <a href="https://www.pinterest.com/dealvault_finds/">Pinterest</a></p></main>'
        builder.write(current,builder.shell(lang,current,c['about'],body,legal='about',summary=c['about_text']))
