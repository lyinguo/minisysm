"""Real supplier creation and paginated picker queries, restricted to QA services."""
import argparse
import json
import uuid
import urllib.parse
from warehouse_acceptance import WarehouseSuite
from acceptance import QA,read_state,sql,literal


class BookingSupplierSuite(WarehouseSuite):
    def prepare(self):
        prefix='QABOOK'+uuid.uuid4().hex[:10]
        items=[]
        for index in range(12):
            name='QA 订单供应商 '+prefix+' '+str(index+1).zfill(2);number=prefix+str(index+1).zfill(2)
            body=dict(name=name,number=number,frame=self.state['frame_id'],user=self.actor,category='常规类别',rate=0,contacts='[]',data='QA supplier picker')
            result=self.request('POST','/basic_information/supplier/add',body,service='basic')
            assert result.get('code')==10000 and result.get('data'),'Actual QA supplier create failed'
            items.append(dict(id=result['data'],name=name,number=number))
        return dict(database=self.state['database'],prefix=prefix,items=items)

    def query(self,**params):
        result=self.request('GET','/basic_information/supplier/querySupplierList?'+urllib.parse.urlencode(dict(pageIndex=1,pageSize=10,**params)),service='basic')
        assert result.get('code')==10000 and isinstance(result.get('data'),dict)
        return result['data']

    def run(self):
        fixture=self.prepare()
        def pagination():
            first=self.query(name=fixture['prefix'])
            result=self.request('GET','/basic_information/supplier/querySupplierList?'+urllib.parse.urlencode(dict(pageIndex=2,pageSize=10,name=fixture['prefix'])),service='basic')
            assert result.get('code')==10000;second=result['data']
            ids={item['id'] for item in first['rows']+second['rows']}
            assert first['total']==12 and second['total']==12 and len(first['rows'])==10 and len(second['rows'])==2
            assert ids=={item['id'] for item in fixture['items']}
            assert sql(self.state,'SELECT COUNT(*) FROM supplier WHERE number LIKE '+literal(fixture['prefix']+'%')+';')=='12'
            return ['Twelve suppliers created through actual API; two actual ten-row pages return all persisted UUIDs exactly once']
        self.case('booking.supplier_actual_pagination',pagination)
        def search():
            target=fixture['items'][-1]
            for key,value in [('name',target['name']),('number',target['number'])]:
                result=self.query(**{key:value});assert result['total']==1 and result['rows'][0]['id']==target['id']
            return ['Actual name-only and code-only queries locate the same persisted UUID without loading the first 500 suppliers']
        self.case('booking.supplier_actual_name_and_number_search',search)
        self.write_report()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['run','prepare'],nargs='?',default='run')
    if parser.parse_args().action=='prepare':
        suite=BookingSupplierSuite(read_state());fixture=suite.prepare()
        (QA/'runtime/booking-supplier-browser.json').write_text(json.dumps(fixture,ensure_ascii=False),encoding='utf-8')
        (QA/'runtime/browser-session.json').write_text(json.dumps(dict(token=suite.token)),encoding='utf-8')
        print('Prepared actual QA supplier query: '+fixture['prefix']+'; selected target '+fixture['items'][-1]['name']+' / '+fixture['items'][-1]['number'])
    else:BookingSupplierSuite(read_state()).run()
