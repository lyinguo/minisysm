-- Add separately selectable permissions for implemented procurement workflows.
-- Preserve all existing function IDs/URLs and every saved role selection.
INSERT INTO func_perm(id,mid,name,url,sort,is_enable)
SELECT 'purchase_supply_manage','086','维护商品供货关系',
       '/j3-purchase/purchase-order/supply/manage',50,'1'
FROM menu m WHERE m.id='086' AND m.resource='/purchase-booking'
AND NOT EXISTS (SELECT 1 FROM func_perm f WHERE f.id='purchase_supply_manage'
 OR f.url='/j3-purchase/purchase-order/supply/manage');

INSERT INTO func_perm(id,mid,name,url,sort,is_enable)
SELECT 'purchase_return_update','090','修改采购退货草稿',
       '/j3-purchase/purchase-return-form/update',50,'1'
FROM menu m WHERE m.id='090' AND m.resource='/purchase-return'
AND NOT EXISTS (SELECT 1 FROM func_perm f WHERE f.id='purchase_return_update'
 OR f.url='/j3-purchase/purchase-return-form/update');
