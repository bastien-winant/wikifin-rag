import scrapy
from crawler.items import DocumentItem
from trafilatura import extract_metadata
from bs4 import BeautifulSoup
from datetime import datetime


def has_class(selector, classname):
    selector_classes = selector.attrib["class"].split()
    return classname in selector_classes


def extract_content(html_str):
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(" ", strip=True)


class PagesSpider(scrapy.Spider):
    name = "pages"
    start_urls = ["https://www.wikifin.be/page/sitemap.xml"]

    custom_settings = {
        'DOWNLOAD_DELAY': 30,
        'ITEM_PIPELINES': {
            "crawler.pipelines.SQLiteUploadPipeline": 300
        }
    }

    def parse(self, response):
        response.selector.remove_namespaces()

        language = getattr(self, "language", None)

        urlset = response.xpath("//urlset")

        if language:
            urls = urlset.xpath(f".//url/link[@hreflang='{language.lower()}']")
        else:
            urls = urlset.xpath(".//url/link").getall()

        yield from response.follow_all(set(urls[:-100]), callback=self.parse_content_page)

        # faq_urls = [url for url in urls if 'faq' in url.attrib['href']]
        # yield from response.follow_all(set(faq_urls), callback=self.parse_content_page)

    def parse_content_page(self, response):
        language = getattr(self, "language", None)

        # extract metadata
        html = response.text
        metadata = extract_metadata(html).as_dict()

        category = metadata.get('title')
        description = metadata.get('description')

        date_str = metadata.get('date')
        date_format = '%Y-%m-%d'
        date = datetime.strptime(date_str, date_format) if date_str else None

        # isolate the main content
        main = response.css("#main-content")[0]
        node = main.css(".node")[0]

        # Save related link URLs
        related_links = node.css('.related-content a::attr("href")').getall()

        # extract the text from main content
        node_content = node.css(".node__content")[0]
        node_paragraph_container = node_content.css(".node__paragraphs")[0]
        node_paragraphs = node_paragraph_container.css(":scope > .paragraph")


        for paragraph in node_paragraphs:
            # skip table of content
            if has_class(paragraph, "paragraph--type--pt-toc"):
                continue

            if has_class(paragraph, "paragraph--type--pt-faq-list"):
                faqs = paragraph.css(".faq")

                for faq in faqs:
                    title = faq.css(".faq__title::text").get().strip()
                    content_html = faq.css(".faq__content").get()
                    content_text = extract_content(content_html)

                    # save the data to the database
                    yield DocumentItem(
                        source_url=response.url,
                        language=language,
                        date=date,
                        category=category,
                        description=description,
                        title=title,
                        html=content_html,
                        content=content_text,
                        related_links=related_links
                    )

            elif has_class(paragraph, "paragraph--type--pt-menu-children"):
                pass
            
            elif has_class(paragraph, "paragraph--type--pt-text"):
                content_html = paragraph.css(".text-content").get()
                content_text = extract_content(content_html)

                if len(paragraph.css(".text-content")) != 1:
                    print(f"NUMBER OF TEXT CONTENT ELEMENTS INSIDE THE PARAGRAPH: {len(paragraph.css(".text-content"))}")

                # save the data to the database
                yield DocumentItem(
                    source_url=response.url,
                    language=language,
                    date=date,
                    category=category,
                    description=description,
                    title=category,
                    html=content_html,
                    content=content_text,
                    related_links=related_links
                )
            
            else:
                print(paragraph.attrib["class"].split())

        # # Recursively follow links
        # links = node.css("a")
        # links = set([link for link in links if link.attrib['href'].startswith(f"/{language}") or
        #                                     link.attrib['href'].startswith(f"https://www.wikifin.be/{language}")])

        # yield from response.follow_all(links, self.parse_content_page)

        # # Recursively follow links
        # links = node.css("a")
        # links = set([link for link in links if (link.attrib['href'].startswith(f"/{language}") or
        #                                     link.attrib['href'].startswith(f"https://www.wikifin.be/{language}"))
        #                                     and ('faq' in link.attrib['href'])])
        
        # yield from response.follow_all(links, self.parse_content_page)