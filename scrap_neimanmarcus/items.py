# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Product(scrapy.Item):

    name = scrapy.Field()
    brand = scrapy.Field()
    sku = scrapy.Field()
    description = scrapy.Field()
    locale = scrapy.Field()
    currency = scrapy.Field()
    product_url = scrapy.Field()
    price = scrapy.Field()
    img_urls = scrapy.Field()
    sizes = scrapy.Field()


class Size(scrapy.Item):

    name = scrapy.Field()
    quantity = scrapy.Field()