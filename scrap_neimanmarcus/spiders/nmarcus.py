import base64
import logging
import time
import json
from scrapy import Spider, Request, FormRequest, Selector
from scrapy.utils.log import configure_logging
from scrap_neimanmarcus.items import Product, Size


class NeimanMarcus(Spider):
    name = "neimanmarcus"

    start_urls = [
        "http://www.neimanmarcus.com/en-pk/index.jsp"
    ]
    custom_settings = {
        'LOG_STDOUT': True,
    }
    configure_logging(settings=None, install_root_handler=True)

    def encode(self, _str):
        return "$b64$" + base64.standard_b64encode(_str).replace('=', '$')

    def parse(self, response):
        url = response.xpath("//ul/li/div[@class='make-relative']/a[contains(.,'Designers')]/@href").extract_first()
        return Request(url, callback= self.parse_designers)

    def parse_designers(self, response):
        designer_urls = response.xpath("//div[@class='designerlink']/a/@href").extract()
        for url in designer_urls:
            cat= response.xpath("//div[@class='designerlink']/a[@href='{}']/@id".format(url)).extract_first()
            url= response.urljoin(url)
            cat= cat.lstrip('a')
            yield Request(url, callback= self.parse_pages, meta={'response':'notjson', 'cat':cat})

    def parse_pages(self, response):
        cat= response.meta['cat']
        if response.meta['response'] == "json":
            response = json.loads(response.body)
            selector = Selector(text=response['GenericSearchResp']['pagingResults']+response['GenericSearchResp']['productResults'], type='html')
        else:
            selector = Selector(text=response.body, type="html")

        prod_urls = selector.css("#productTemplateId::attr(href)").extract()
        for url in prod_urls:
            url = "http://www.neimanmarcus.com%s" % url
            yield Request(url, callback=self.parse_products)

        nextpage = selector.css("li.pagingSlide.active.pagingNav.next::attr(pagenum)").extract_first()
        ts = long(time.time())
        ts = str(ts)
        if nextpage is not None:
            offset = int(nextpage)-1
            offset = str(offset)
            data = '{"GenericSearchReq":{"pageOffset":%s,"pageSize":"30","refinements":"","selectedRecentSize":"","activeFavoriteSizesCount":"0","activeInteraction":"true","mobile":false,"sort":"","personalizedPriorityProdId":"x","endecaDrivenSiloRefinements":"navAction=index","definitionPath":"/nm/commerce/pagedef_rwd/template/EndecaDrivenHome","userConstrainedResults":"true","updateFilter":"false","rwd":"true","advancedFilterReqItems":{"StoreLocationFilterReq":[{"allStoresInput":"false","onlineOnly":""}]},"categoryId":"%s","sortByFavorites":false,"isFeaturedSort":true,"prevSort":""}}' % (offset, cat)
            encoded_data = self.encode(data)
            encoded_data = str(encoded_data)
            frmdata = {"data": encoded_data,'service':'getCategoryGrid','sid':'getCategoryGrid','bid':'GenericSearchReq','timestamp':ts}
            yield FormRequest(
                                url ="http://www.neimanmarcus.com/en-pk/category.service?instart_disable_injection=true",
                                formdata= frmdata,
                                callback=self.parse_pages,
                                headers={'Content-Type':'application/x-www-form-urlencoded'},
                                meta={'response':'json', 'cat': cat}
                             )

    def parse_products(self, response):
        prod = Product()
        ts = long(time.time())
        ts = str(ts)
        prod['name']= response.xpath("//div[@id='productDetails']/div/h1/span[@itemprop='name']/text()").extract_first()
        prod['brand']= response.xpath("//div[@id='productDetails']//span[@itemprop='brand']//text()").extract_first()
        prod['price']= response.xpath("//div[@id='productDetails']//*[@itemprop='price']/text()").extract_first().strip()
        prod['locale']=[response.xpath("/html/@lang").extract_first(), response.xpath("//input[@class='intl-countrycode']/@value").extract_first()]
        prod['locale']= "-".join(prod['locale'])
        prod['currency']= response.xpath("//div[@id='productDetails']//meta[@itemprop='priceCurrency']/@content").extract_first()
        prod['description']= response.xpath("(//div[@id='productDetails'])[1]//div[@itemprop='description']//ul/li/text()").extract()
        prod['img_urls']= response.xpath("(//div[@class='images'])[1]//div[@class='product-thumbnails elim-suites hide-on-mobile']//li//img/@src").extract()
        prod['product_url']= response.url
        prod_id = response.xpath("//div[contains(@class,'product-details-source elim-suites')]/@class").extract_first()
        prod_id = prod_id.split(" ")[-1]
        url= "http://www.neimanmarcus.com/en-pk/product.service?instart_disable_injection=true"
        data = '{"ProductSizeAndColor":{"productIds":"%s"}}' % prod_id
        encoded_data = self.encode(data)
        frmdata= {"data": encoded_data, "sid":"getSizeAndColorData", "bid":"ProductSizeAndColor","timestamp":ts}
        return FormRequest(url, callback=self.parse_sizes, formdata=frmdata, meta={'item':prod})

    def parse_sizes(self, response):
        prod = response.meta['item']
        response = json.loads(response.body)
        prod['sizes'] = list()
        details = response["ProductSizeAndColor"]["productSizeAndColorJSON"]
        details = json.loads(details)
        for sku in details[0]["skus"]:
            size = Size()
            size['name']= sku['size']
            size['quantity']= sku['stockAvailable']
            prod['sizes'].append(size)
        return prod