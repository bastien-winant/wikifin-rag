import scrapy
from crawler.items import DocumentItem
from trafilatura import fetch_url, extract, bare_extraction, extract_metadata
from datetime import datetime


def has_class(selector, classname):
    selector_classes = selector.attrib["class"].split()
    return classname in selector_classes


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

        yield from response.follow_all(urls[:2], callback=self.parse_content_page)


    def parse_content_page(self, response):
        language = getattr(self, "language", None)

        # extract metadata
        html = response.text
        metadata = extract_metadata(html).as_dict()

        title = metadata.get('title')
        description = metadata.get('description')

        date_str = metadata.get('date')
        date_format = '%Y-%m-%d'
        date = datetime.strptime(date_str, date_format) if date_str else None

        main = response.css("#main-content")[0]
        node = main.css(".node")[0]

        # TODO: extract the text from node_content
        html_content = node.css(".node__content").get()
        text_content = extract(
            html_content,
            output_format="markdown",
            include_links=False,
            include_tables=True,
            include_formatting=False)

        # Recursively follow links
        links = node.css("a")
        links = [link for link in links if link.attrib['href'].startswith(f"/{language}") or
                                            link.attrib['href'].startswith(f"https://www.wikifin.be/{language}")]

        yield from response.follow_all(links, self.parse_content_page)

        # Save related link URLs
        related_links = node.css('.related-content a::attr("href")').getall()
        related_links = ", ".join(related_links)

        # save the data to the database
        yield DocumentItem(
            source_url=response.url,
            language=language,
            title=title,
            description=description,
            date=date,
            html=html_content,
            content=text_content,
            related_links=related_links
        )

        #     paragraphs = []
        #     links = []

        #     if has_class(node, "node--type-ct-faq"):
        #         header = node_content.css(".faq__header")[0]
        #         title = header.css(".faq__title::text").get().strip()

        #         paragraphs_container = node_content.css(".faq__content")[0]
        #         paragraphs = paragraphs_container.css(".paragraph")

        #     elif has_class(node, "node--type-ct-page"):
        #         header = node_content.css(".node__header")[0]
        #         title = header.css(".node__title::text").get().strip()

        #         paragraphs_container = node_content.css(".node__paragraphs")[0]
        #         paragraphs = paragraphs_container.css(".paragraph")
        #     else:
        #         print("=============================================")
        #         print("DIFFERENT NODE TYPE")
        #         print("NODE CLASSES: ", node.attrib["class"].split())
        #         print("==============================================")
        #         continue

        #     text_content = ""
        #     for paragraph in paragraphs:
        #         # skip table of content
        #         if has_class(paragraph, 'paragraph--type--pt-toc'):
        #             continue

                    # if has_class

        #         # retrieve all text content
        #         if has_class(paragraph, 'paragraph--type--pt-text'):
        #             text = " ".join(paragraph.xpath(".//text()").getall()).strip()
        #             text_content += "\n" + text

        #         paragraph_links = paragraph.css("a")
        #         paragraph_links = [link for link in paragraph_links if
        #                            link.attrib['href'].startswith(f"/{language}") or
        #                            link.attrib['href'].startswith(f"https://www.wikifin.be/{language}")]
        #         links.extend(paragraph_links)

        #     yield from response.follow_all(links, self.parse_content_page)
            
        #     yield DocumentItem(
        #         source_url=response.url,
        #         language=language,
        #         title=title,
        #         content=text_content,
        #         content_html=content_html
        #     )
