"""Actual sales HTTP/MySQL date parsing gates, including invalid-date persistence protection."""
from datetime import datetime,timezone,timedelta
from sale_draft_acceptance import SaleDraftSuite
from acceptance import read_state,sql,literal


class SaleBusinessTimeSuite(SaleDraftSuite):
    def run(self):
        def formats():
            epoch=int(datetime(2026,11,15,11,42,33,tzinfo=timezone(timedelta(hours=8))).timestamp()*1000)
            for value,expected in [('2026-11-15','2026-11-15 00:00:00'),('2026-11-15 11:42:33','2026-11-15 11:42:33'),('2026-11-15T11:42:33+08:00','2026-11-15 11:42:33'),('2026-11-15T03:42:33Z','2026-11-15 11:42:33'),(epoch,'2026-11-15 11:42:33')]:
                body=self.body();body['time']=value;identifier=self.create(body)
                assert sql(self.state,"SELECT DATE_FORMAT(time,'%Y-%m-%d %H:%i:%s') FROM sell WHERE id="+literal(identifier)+';')==expected,'Sales business time changed for '+str(value)
            return ['Actual create persists whole date, local seconds, ISO offset/Z and epoch timestamps in Shanghai business time']
        self.case('sale.time_actual_supported_formats',formats)

        def invalid():
            for value in ['2026-02-30','2026-11-15 25:00:00','2026-11-15 garbage']:
                body=self.body();body['time']=value
                assert self.request('POST','/sale/form/addSale',body,service='sale').get('code')!=10000,'Invalid business date accepted'
                assert sql(self.state,'SELECT COUNT(*) FROM sell WHERE number='+literal(body['number'])+';')=='0','Invalid date persisted a sale'
            return ['Invalid calendar date, invalid hour and trailing text reject before persistence']
        self.case('sale.time_invalid_date_no_persistence',invalid)
        self.write_report()


if __name__=='__main__':SaleBusinessTimeSuite(read_state()).run()
