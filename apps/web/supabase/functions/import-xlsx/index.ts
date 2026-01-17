import "https://deno.land/x/xhr@0.1.0/mod.ts";
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.3";
import * as XLSX from "https://esm.sh/xlsx@0.18.5";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

const BATCH_SIZE = 100; // Process rows in batches

function detectReportType(headers: string[]): string | null {
  const headerSet = new Set(headers.map(h => h?.trim()));
  
  if (headerSet.has('Логистический сбор') && headerSet.has('№ заказа')) {
    return 'sales';
  }
  if (headerSet.has('ID операции') && headerSet.has('Тип операции')) {
    return 'expenses';
  }
  if (headerSet.has('Индикатор обеспеченности') && headerSet.has('Рекомендованное количество на поставку, шт')) {
    return 'inventory';
  }
  if (headerSet.has('Оборачиваемость, дней') && headerSet.has('Габаритная группа')) {
    return 'storage';
  }
  
  return null;
}

function parseDate(value: any): string | null {
  if (!value) return null;
  
  if (typeof value === 'number') {
    const date = XLSX.SSF.parse_date_code(value);
    if (date) {
      return `${date.y}-${String(date.m).padStart(2, '0')}-${String(date.d).padStart(2, '0')}T${String(date.H || 0).padStart(2, '0')}:${String(date.M || 0).padStart(2, '0')}:00`;
    }
  }
  
  if (typeof value === 'string') {
    const match = value.match(/(\d{2})\.(\d{2})\.(\d{4})\s*(\d{2})?:?(\d{2})?/);
    if (match) {
      const [, day, month, year, hour = '00', minute = '00'] = match;
      return `${year}-${month}-${day}T${hour}:${minute}:00`;
    }
    
    if (value.includes('-') || value.includes('T')) {
      return value;
    }
  }
  
  return null;
}

function parseNumber(value: any): number {
  if (value === null || value === undefined || value === '') return 0;
  if (typeof value === 'number') return value;
  if (typeof value === 'string') {
    const cleaned = value.replace(/\s/g, '').replace(',', '.');
    const num = parseFloat(cleaned);
    return isNaN(num) ? 0 : num;
  }
  return 0;
}

function parseBoolean(value: any): boolean {
  if (!value) return false;
  const str = String(value).toLowerCase().trim();
  return str === 'да' || str === 'yes' || str === 'true' || str === '1';
}

function getColumnIndex(headers: string[], columnName: string): number {
  return headers.findIndex(h => h && h.includes(columnName));
}

function getCellValue(row: any[], headers: string[], columnName: string): any {
  const index = getColumnIndex(headers, columnName);
  return index >= 0 ? row[index] : null;
}

// Cache for shops, products, variants to reduce DB lookups
const shopCache = new Map<string, string>();
const productCache = new Map<string, string>();
const variantCache = new Map<string, string>();

async function getOrCreateShop(supabase: any, userId: string, shopName: string): Promise<string | null> {
  if (!shopName) return null;
  
  const cacheKey = `${userId}-${shopName}`;
  if (shopCache.has(cacheKey)) {
    return shopCache.get(cacheKey)!;
  }
  
  const { data: existing } = await supabase
    .from('shops')
    .select('id')
    .eq('user_id', userId)
    .eq('name', shopName)
    .maybeSingle();
  
  if (existing) {
    shopCache.set(cacheKey, existing.id);
    return existing.id;
  }
  
  const { data: newShop, error } = await supabase
    .from('shops')
    .insert({ name: shopName, user_id: userId })
    .select('id')
    .single();
  
  if (error) {
    console.error('Error creating shop:', error);
    return null;
  }
  
  shopCache.set(cacheKey, newShop.id);
  return newShop?.id || null;
}

async function getOrCreateProduct(
  supabase: any, 
  shopId: string | null, 
  uzumProductId: string, 
  productName: string,
  category: string | null
): Promise<string | null> {
  if (!uzumProductId) return null;
  
  if (productCache.has(uzumProductId)) {
    return productCache.get(uzumProductId)!;
  }
  
  const { data: existing } = await supabase
    .from('products')
    .select('id')
    .eq('uzum_product_id', uzumProductId)
    .maybeSingle();
  
  if (existing) {
    productCache.set(uzumProductId, existing.id);
    return existing.id;
  }
  
  const { data: newProduct, error } = await supabase
    .from('products')
    .insert({ 
      uzum_product_id: uzumProductId, 
      name: productName || 'Unknown',
      category: category,
      shop_id: shopId,
    })
    .select('id')
    .single();
  
  if (error) {
    console.error('Error creating product:', error);
    return null;
  }
  
  productCache.set(uzumProductId, newProduct.id);
  return newProduct?.id || null;
}

async function getOrCreateVariant(
  supabase: any,
  productId: string,
  barcode: string,
  sku: string,
  dimensionGroup: string | null
): Promise<string | null> {
  if (!barcode) return null;
  
  if (variantCache.has(barcode)) {
    return variantCache.get(barcode)!;
  }
  
  const { data: existing } = await supabase
    .from('product_variants')
    .select('id')
    .eq('barcode', barcode)
    .maybeSingle();
  
  if (existing) {
    variantCache.set(barcode, existing.id);
    return existing.id;
  }
  
  const { data: newVariant, error } = await supabase
    .from('product_variants')
    .insert({ 
      product_id: productId,
      barcode: barcode,
      sku: sku || '',
      dimension_group: dimensionGroup,
    })
    .select('id')
    .single();
  
  if (error) {
    console.error('Error creating variant:', error);
    return null;
  }
  
  variantCache.set(barcode, newVariant.id);
  return newVariant?.id || null;
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader?.startsWith('Bearer ')) {
      console.error('Missing or invalid authorization header');
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY')!;
    
    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      global: { headers: { Authorization: authHeader } }
    });

    const token = authHeader.replace('Bearer ', '');
    const { data: claimsData, error: claimsError } = await supabase.auth.getUser(token);
    if (claimsError || !claimsData?.user) {
      console.error('Auth error:', claimsError);
      return new Response(
        JSON.stringify({ error: 'Unauthorized' }),
        { status: 401, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }
    
    const userId = claimsData.user.id;
    console.log('Processing upload for user:', userId);

    // Clear caches for new upload
    shopCache.clear();
    productCache.clear();
    variantCache.clear();

    const formData = await req.formData();
    const file = formData.get('file') as File;
    const reportType = formData.get('reportType') as string;
    const fileName = formData.get('fileName') as string;

    if (!file) {
      return new Response(
        JSON.stringify({ error: 'No file provided' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log(`Processing file: ${fileName}, type: ${reportType}, size: ${file.size}`);

    const arrayBuffer = await file.arrayBuffer();
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array', cellDates: true });
    
    const sheetName = workbook.SheetNames[0];
    const worksheet = workbook.Sheets[sheetName];
    
    const rawData: any[][] = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: null });
    
    if (rawData.length < 2) {
      return new Response(
        JSON.stringify({ error: 'File is empty or has no data rows' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    let headerRowIndex = 0;
    for (let i = 0; i < Math.min(5, rawData.length); i++) {
      const row = rawData[i];
      if (row && row.some((cell: any) => 
        typeof cell === 'string' && 
        (cell.includes('Штрихкод') || cell.includes('ID операции') || cell.includes('Статус'))
      )) {
        headerRowIndex = i;
        break;
      }
    }

    const headers = rawData[headerRowIndex].map((h: any) => String(h || '').trim());
    const dataRows = rawData.slice(headerRowIndex + 1);

    const detectedType = reportType || detectReportType(headers);
    if (!detectedType) {
      console.error('Could not detect report type. Headers:', headers);
      return new Response(
        JSON.stringify({ error: 'Could not detect report type from file structure' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    console.log(`Detected report type: ${detectedType}, rows to process: ${dataRows.length}`);

    // Clear existing data for this report type before importing new data
    console.log(`Clearing existing ${detectedType} data for user ${userId}...`);
    
    if (detectedType === 'sales') {
      // Get user's shops to filter sales
      const { data: userShops } = await supabase
        .from('shops')
        .select('id')
        .eq('user_id', userId);
      
      if (userShops && userShops.length > 0) {
        const shopIds = userShops.map((s: any) => s.id);
        
        // Get products for user's shops
        const { data: userProducts } = await supabase
          .from('products')
          .select('id')
          .in('shop_id', shopIds);
        
        if (userProducts && userProducts.length > 0) {
          const productIds = userProducts.map((p: any) => p.id);
          
          // Get variants for user's products
          const { data: userVariants } = await supabase
            .from('product_variants')
            .select('id')
            .in('product_id', productIds);
          
          if (userVariants && userVariants.length > 0) {
            const variantIds = userVariants.map((v: any) => v.id);
            
            // Delete sales for user's variants
            const { error: deleteError } = await supabase
              .from('sales')
              .delete()
              .in('variant_id', variantIds);
            
            if (deleteError) {
              console.error('Error clearing sales:', deleteError);
            } else {
              console.log('Sales data cleared successfully');
            }
          }
        }
      }
      
      // Also delete old upload records for this type
      await supabase
        .from('report_uploads')
        .delete()
        .eq('user_id', userId)
        .eq('report_type', 'sales');
        
    } else if (detectedType === 'expenses') {
      // Delete expenses through upload records
      const { data: oldUploads } = await supabase
        .from('report_uploads')
        .select('id')
        .eq('user_id', userId)
        .eq('report_type', 'expenses');
      
      if (oldUploads && oldUploads.length > 0) {
        const uploadIds = oldUploads.map((u: any) => u.id);
        
        await supabase
          .from('expenses')
          .delete()
          .in('upload_id', uploadIds);
      }
      
      await supabase
        .from('report_uploads')
        .delete()
        .eq('user_id', userId)
        .eq('report_type', 'expenses');
        
      console.log('Expenses data cleared successfully');
      
    } else if (detectedType === 'inventory') {
      // Delete inventory snapshots through variants
      const { data: userShops } = await supabase
        .from('shops')
        .select('id')
        .eq('user_id', userId);
      
      if (userShops && userShops.length > 0) {
        const shopIds = userShops.map((s: any) => s.id);
        
        const { data: userProducts } = await supabase
          .from('products')
          .select('id')
          .in('shop_id', shopIds);
        
        if (userProducts && userProducts.length > 0) {
          const productIds = userProducts.map((p: any) => p.id);
          
          const { data: userVariants } = await supabase
            .from('product_variants')
            .select('id')
            .in('product_id', productIds);
          
          if (userVariants && userVariants.length > 0) {
            const variantIds = userVariants.map((v: any) => v.id);
            
            await supabase
              .from('inventory_snapshots')
              .delete()
              .in('variant_id', variantIds);
          }
        }
      }
      
      await supabase
        .from('report_uploads')
        .delete()
        .eq('user_id', userId)
        .eq('report_type', 'inventory');
        
      console.log('Inventory data cleared successfully');
      
    } else if (detectedType === 'storage') {
      // Delete storage costs through variants
      const { data: userShops } = await supabase
        .from('shops')
        .select('id')
        .eq('user_id', userId);
      
      if (userShops && userShops.length > 0) {
        const shopIds = userShops.map((s: any) => s.id);
        
        const { data: userProducts } = await supabase
          .from('products')
          .select('id')
          .in('shop_id', shopIds);
        
        if (userProducts && userProducts.length > 0) {
          const productIds = userProducts.map((p: any) => p.id);
          
          const { data: userVariants } = await supabase
            .from('product_variants')
            .select('id')
            .in('product_id', productIds);
          
          if (userVariants && userVariants.length > 0) {
            const variantIds = userVariants.map((v: any) => v.id);
            
            await supabase
              .from('storage_costs')
              .delete()
              .in('variant_id', variantIds);
          }
        }
      }
      
      await supabase
        .from('report_uploads')
        .delete()
        .eq('user_id', userId)
        .eq('report_type', 'storage');
        
      console.log('Storage costs data cleared successfully');
    }

    const { data: uploadRecord, error: uploadError } = await supabase
      .from('report_uploads')
      .insert({
        user_id: userId,
        report_type: detectedType,
        file_name: fileName,
        status: 'processing',
        rows_imported: 0,
      })
      .select()
      .single();

    if (uploadError) {
      console.error('Error creating upload record:', uploadError);
      return new Response(
        JSON.stringify({ error: 'Failed to create upload record' }),
        { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const uploadId = uploadRecord.id;
    let rowsImported = 0;
    let errors: string[] = [];

    if (detectedType === 'sales') {
      rowsImported = await processSalesReport(supabase, userId, uploadId, headers, dataRows, errors);
    } else if (detectedType === 'expenses') {
      rowsImported = await processExpensesReport(supabase, uploadId, headers, dataRows, errors);
    } else if (detectedType === 'inventory') {
      rowsImported = await processInventoryReport(supabase, userId, uploadId, headers, dataRows, errors);
    } else if (detectedType === 'storage') {
      rowsImported = await processStorageReport(supabase, userId, uploadId, headers, dataRows, errors);
    }

    await supabase
      .from('report_uploads')
      .update({
        status: errors.length > 0 ? 'completed_with_errors' : 'completed',
        rows_imported: rowsImported,
        error_message: errors.length > 0 ? errors.slice(0, 5).join('; ') : null,
      })
      .eq('id', uploadId);

    console.log(`Import completed: ${rowsImported} rows, ${errors.length} errors`);

    return new Response(
      JSON.stringify({
        success: true,
        reportType: detectedType,
        rowsImported,
        errors: errors.slice(0, 10),
        uploadId,
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );

  } catch (error: any) {
    console.error('Error processing file:', error);
    return new Response(
      JSON.stringify({ error: error.message || 'Internal server error' }),
      { status: 500, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    );
  }
});

async function processSalesReport(
  supabase: any,
  userId: string,
  uploadId: string,
  headers: string[],
  dataRows: any[][],
  errors: string[]
): Promise<number> {
  let imported = 0;
  
  const { data: userShops } = await supabase
    .from('shops')
    .select('id')
    .eq('user_id', userId)
    .limit(1);
  
  let defaultShopId = userShops?.[0]?.id;
  if (!defaultShopId) {
    const { data: newShop } = await supabase
      .from('shops')
      .insert({ name: 'Мой магазин', user_id: userId })
      .select('id')
      .single();
    defaultShopId = newShop?.id;
  }

  // First pass: collect all unique products and variants
  const productsToCreate = new Map<string, { name: string; category: string | null }>();
  const variantsToCreate = new Map<string, { productKey: string; sku: string }>();
  
  for (const row of dataRows) {
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
    const sku = String(getCellValue(row, headers, 'SKU') || '').trim();
    const productName = String(getCellValue(row, headers, 'Наименование') || '').trim();
    const category = String(getCellValue(row, headers, 'Категория') || '').trim();
    
    if (!barcode) continue;
    
    const productKey = barcode.substring(0, 10);
    if (!productsToCreate.has(productKey)) {
      productsToCreate.set(productKey, { name: productName, category: category || null });
    }
    if (!variantsToCreate.has(barcode)) {
      variantsToCreate.set(barcode, { productKey, sku });
    }
  }

  // Ensure all products exist
  for (const [productKey, data] of productsToCreate) {
    await getOrCreateProduct(supabase, defaultShopId, productKey, data.name, data.category);
  }

  // Ensure all variants exist
  for (const [barcode, data] of variantsToCreate) {
    const productId = productCache.get(data.productKey);
    if (productId) {
      await getOrCreateVariant(supabase, productId, barcode, data.sku, null);
    }
  }

  // Batch insert sales
  const salesBatch: any[] = [];
  
  for (let i = 0; i < dataRows.length; i++) {
    const row = dataRows[i];
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    try {
      const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
      const orderNumber = String(getCellValue(row, headers, '№ заказа') || '').trim();
      
      if (!barcode) continue;

      const variantId = variantCache.get(barcode);
      if (!variantId) continue;

      const rowHash = `${orderNumber}-${barcode}-${getCellValue(row, headers, 'Дата создания')}`;

      salesBatch.push({
        upload_id: uploadId,
        variant_id: variantId,
        status: String(getCellValue(row, headers, 'Статус') || ''),
        order_number: orderNumber,
        created_date: parseDate(getCellValue(row, headers, 'Дата создания')),
        received_date: parseDate(getCellValue(row, headers, 'Дата получения')),
        quantity: parseNumber(getCellValue(row, headers, 'Количество')),
        returns: parseNumber(getCellValue(row, headers, 'Возвраты')),
        revenue: parseNumber(getCellValue(row, headers, 'Выручка (сумы)')),
        revenue_net: parseNumber(getCellValue(row, headers, 'Выручка с вычетом комиссии')),
        marketplace_commission: parseNumber(getCellValue(row, headers, 'Комиссия маркетплейса')),
        price: parseNumber(getCellValue(row, headers, 'Цена (сумы)')),
        promo_discount: parseNumber(getCellValue(row, headers, 'Промокод')),
        cost_price: parseNumber(getCellValue(row, headers, 'Себестоимость')),
        logistics_fee: parseNumber(getCellValue(row, headers, 'Логистический сбор')),
        source_row_hash: rowHash,
      });

      // Insert in batches
      if (salesBatch.length >= BATCH_SIZE) {
        const { data: insertedData, error: insertError } = await supabase
          .from('sales')
          .insert(salesBatch)
          .select('id');
        
        if (insertError) {
          console.error('Batch insert error:', insertError);
          errors.push(`Batch error: ${insertError.message}`);
        } else {
          imported += insertedData?.length || 0;
        }
        salesBatch.length = 0;
      }
    } catch (e: any) {
      errors.push(`Row ${i + 1}: ${e.message}`);
    }
  }

  // Insert remaining
  if (salesBatch.length > 0) {
    const { data: insertedData, error: insertError } = await supabase
      .from('sales')
      .insert(salesBatch)
      .select('id');
    
    if (insertError) {
      console.error('Batch insert error:', insertError);
      errors.push(`Batch error: ${insertError.message}`);
    } else {
      imported += insertedData?.length || 0;
    }
  }
  
  return imported;
}

async function processExpensesReport(
  supabase: any,
  uploadId: string,
  headers: string[],
  dataRows: any[][],
  errors: string[]
): Promise<number> {
  let imported = 0;
  const expensesBatch: any[] = [];
  
  for (let i = 0; i < dataRows.length; i++) {
    const row = dataRows[i];
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    try {
      const operationId = String(getCellValue(row, headers, 'ID операции') || '').trim();
      if (!operationId) continue;

      expensesBatch.push({
        upload_id: uploadId,
        source: String(getCellValue(row, headers, 'Источник') || ''),
        service_description: String(getCellValue(row, headers, 'Услуга') || ''),
        status: String(getCellValue(row, headers, 'Статус') || ''),
        operation_id: operationId,
        write_off_date: parseDate(getCellValue(row, headers, 'Дата списания')),
        unit_cost: parseNumber(getCellValue(row, headers, 'Стоимость (сумы)')),
        quantity: parseNumber(getCellValue(row, headers, 'Количество')),
        total_amount: parseNumber(getCellValue(row, headers, 'Сумма (сумы)')),
        operation_type: String(getCellValue(row, headers, 'Тип операции') || ''),
      });

      if (expensesBatch.length >= BATCH_SIZE) {
        const { data: insertedData, error: insertError } = await supabase
          .from('expenses')
          .insert(expensesBatch)
          .select('id');
        
        if (insertError) {
          console.error('Batch insert error:', insertError);
          errors.push(`Batch error: ${insertError.message}`);
        } else {
          imported += insertedData?.length || 0;
        }
        expensesBatch.length = 0;
      }
    } catch (e: any) {
      errors.push(`Row ${i + 1}: ${e.message}`);
    }
  }

  if (expensesBatch.length > 0) {
    const { data: insertedData, error: insertError } = await supabase
      .from('expenses')
      .insert(expensesBatch)
      .select('id');
    
    if (insertError) {
      console.error('Batch insert error:', insertError);
      errors.push(`Batch error: ${insertError.message}`);
    } else {
      imported += insertedData?.length || 0;
    }
  }
  
  return imported;
}

async function processInventoryReport(
  supabase: any,
  userId: string,
  uploadId: string,
  headers: string[],
  dataRows: any[][],
  errors: string[]
): Promise<number> {
  let imported = 0;
  const snapshotDate = new Date().toISOString().split('T')[0];
  
  // First pass: collect all unique shops, products, variants
  for (const row of dataRows) {
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
    const sku = String(getCellValue(row, headers, 'SKU') || '').trim();
    const shopName = String(getCellValue(row, headers, 'Магазин') || '').trim();
    const productName = String(getCellValue(row, headers, 'Название товара') || '').trim();
    const uzumProductId = String(getCellValue(row, headers, 'ID товара') || '').trim();
    
    if (!barcode) continue;

    const shopId = await getOrCreateShop(supabase, userId, shopName);
    const productId = await getOrCreateProduct(supabase, shopId, uzumProductId, productName, null);
    if (productId) {
      await getOrCreateVariant(supabase, productId, barcode, sku, null);
    }
  }

  // Batch insert inventory
  const inventoryBatch: any[] = [];
  
  for (let i = 0; i < dataRows.length; i++) {
    const row = dataRows[i];
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    try {
      const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
      if (!barcode) continue;

      const variantId = variantCache.get(barcode);
      if (!variantId) continue;

      inventoryBatch.push({
        upload_id: uploadId,
        variant_id: variantId,
        snapshot_date: snapshotDate,
        is_running_out: parseBoolean(getCellValue(row, headers, 'Заканчивается')),
        availability_indicator: String(getCellValue(row, headers, 'Индикатор обеспеченности') || ''),
        planned_stockout_date: parseDate(getCellValue(row, headers, 'Плановая дата')),
        availability_days: parseNumber(getCellValue(row, headers, 'Обеспеченность')),
        recommended_supply_qty: parseNumber(getCellValue(row, headers, 'Рекомендованное количество')),
        fbs_stock: parseNumber(getCellValue(row, headers, 'На вашей стороне')),
        marketplace_total: parseNumber(getCellValue(row, headers, 'На стороне маркетплейса')),
        in_supply: parseNumber(getCellValue(row, headers, 'В поставке')),
        in_sale: parseNumber(getCellValue(row, headers, 'В продаже')),
        in_transit_to_client: parseNumber(getCellValue(row, headers, 'В пути до клиента')),
        in_transit_from_client: parseNumber(getCellValue(row, headers, 'В пути от клиента')),
        long_term_storage: parseNumber(getCellValue(row, headers, 'На складе длительного хранения')),
        at_photo_studio: parseNumber(getCellValue(row, headers, 'На фотостудии')),
        defective: parseNumber(getCellValue(row, headers, 'Брак')),
        potential_revenue_per_unit: parseNumber(getCellValue(row, headers, 'Потенциальная сумма к получению за 1 шт')),
        potential_revenue_total: parseNumber(getCellValue(row, headers, 'Потенциальная сумма к получению за все')),
      });

      if (inventoryBatch.length >= BATCH_SIZE) {
        const { data: insertedData, error: insertError } = await supabase
          .from('inventory_snapshots')
          .insert(inventoryBatch)
          .select('id');
        
        if (insertError) {
          errors.push(`Batch error: ${insertError.message}`);
        } else {
          imported += insertedData?.length || 0;
        }
        inventoryBatch.length = 0;
      }
    } catch (e: any) {
      errors.push(`Row ${i + 1}: ${e.message}`);
    }
  }

  if (inventoryBatch.length > 0) {
    const { data: insertedData, error: insertError } = await supabase
      .from('inventory_snapshots')
      .insert(inventoryBatch)
      .select('id');
    
    if (insertError) {
      errors.push(`Batch error: ${insertError.message}`);
    } else {
      imported += insertedData?.length || 0;
    }
  }
  
  return imported;
}

async function processStorageReport(
  supabase: any,
  userId: string,
  uploadId: string,
  headers: string[],
  dataRows: any[][],
  errors: string[]
): Promise<number> {
  let imported = 0;
  const snapshotDate = new Date().toISOString().split('T')[0];
  
  // First pass: collect all unique shops, products, variants
  for (const row of dataRows) {
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
    const sku = String(getCellValue(row, headers, 'SKU') || '').trim();
    const shopName = String(getCellValue(row, headers, 'Магазин') || '').trim();
    const productName = String(getCellValue(row, headers, 'Название товара') || '').trim();
    const uzumProductId = String(getCellValue(row, headers, 'ID товара') || '').trim();
    const dimensionGroup = String(getCellValue(row, headers, 'Габаритная группа') || '').trim();
    
    if (!barcode) continue;

    const shopId = await getOrCreateShop(supabase, userId, shopName);
    const productId = await getOrCreateProduct(supabase, shopId, uzumProductId, productName, null);
    if (productId) {
      await getOrCreateVariant(supabase, productId, barcode, sku, dimensionGroup);
    }
  }

  // Batch insert storage costs
  const storageBatch: any[] = [];
  
  for (let i = 0; i < dataRows.length; i++) {
    const row = dataRows[i];
    if (!row || row.every((cell: any) => cell === null || cell === '')) continue;
    
    try {
      const barcode = String(getCellValue(row, headers, 'Штрихкод') || '').trim();
      if (!barcode) continue;

      const variantId = variantCache.get(barcode);
      if (!variantId) continue;

      storageBatch.push({
        upload_id: uploadId,
        variant_id: variantId,
        snapshot_date: snapshotDate,
        avg_daily_stock_15d: parseNumber(getCellValue(row, headers, 'Среднесуточные остатки FBO')),
        avg_daily_sales_15d: parseNumber(getCellValue(row, headers, 'Среднесуточные продажи FBO')),
        turnover_days: parseNumber(getCellValue(row, headers, 'Оборачиваемость')),
        storage_type: String(getCellValue(row, headers, 'Хранение') || ''),
        daily_storage_cost_per_unit: parseNumber(getCellValue(row, headers, 'За хранение 1 единицы')),
        fbo_stock_total: parseNumber(getCellValue(row, headers, 'Остатки FBO')),
        daily_storage_cost_total: parseNumber(getCellValue(row, headers, 'Всего за хранение 1 день')),
        monthly_storage_cost: parseNumber(getCellValue(row, headers, 'Всего за хранение последние 30')),
      });

      if (storageBatch.length >= BATCH_SIZE) {
        const { data: insertedData, error: insertError } = await supabase
          .from('storage_costs')
          .insert(storageBatch)
          .select('id');
        
        if (insertError) {
          errors.push(`Batch error: ${insertError.message}`);
        } else {
          imported += insertedData?.length || 0;
        }
        storageBatch.length = 0;
      }
    } catch (e: any) {
      errors.push(`Row ${i + 1}: ${e.message}`);
    }
  }

  if (storageBatch.length > 0) {
    const { data: insertedData, error: insertError } = await supabase
      .from('storage_costs')
      .insert(storageBatch)
      .select('id');
    
    if (insertError) {
      errors.push(`Batch error: ${insertError.message}`);
    } else {
      imported += insertedData?.length || 0;
    }
  }
  
  return imported;
}
