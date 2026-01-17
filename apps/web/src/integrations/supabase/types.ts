export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.1"
  }
  public: {
    Tables: {
      expenses: {
        Row: {
          created_at: string
          id: string
          operation_id: string | null
          operation_type: string | null
          quantity: number | null
          service_description: string | null
          source: string | null
          source_row_hash: string | null
          status: string | null
          total_amount: number | null
          unit_cost: number | null
          upload_id: string | null
          write_off_date: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          operation_id?: string | null
          operation_type?: string | null
          quantity?: number | null
          service_description?: string | null
          source?: string | null
          source_row_hash?: string | null
          status?: string | null
          total_amount?: number | null
          unit_cost?: number | null
          upload_id?: string | null
          write_off_date?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          operation_id?: string | null
          operation_type?: string | null
          quantity?: number | null
          service_description?: string | null
          source?: string | null
          source_row_hash?: string | null
          status?: string | null
          total_amount?: number | null
          unit_cost?: number | null
          upload_id?: string | null
          write_off_date?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "expenses_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "report_uploads"
            referencedColumns: ["id"]
          },
        ]
      }
      inventory_snapshots: {
        Row: {
          at_photo_studio: number | null
          availability_days: number | null
          availability_indicator: string | null
          created_at: string
          defective: number | null
          fbs_stock: number | null
          id: string
          in_sale: number | null
          in_supply: number | null
          in_transit_from_client: number | null
          in_transit_to_client: number | null
          is_running_out: boolean | null
          long_term_storage: number | null
          marketplace_total: number | null
          planned_stockout_date: string | null
          potential_revenue_per_unit: number | null
          potential_revenue_total: number | null
          recommended_supply_qty: number | null
          snapshot_date: string
          source_row_hash: string | null
          upload_id: string | null
          variant_id: string | null
        }
        Insert: {
          at_photo_studio?: number | null
          availability_days?: number | null
          availability_indicator?: string | null
          created_at?: string
          defective?: number | null
          fbs_stock?: number | null
          id?: string
          in_sale?: number | null
          in_supply?: number | null
          in_transit_from_client?: number | null
          in_transit_to_client?: number | null
          is_running_out?: boolean | null
          long_term_storage?: number | null
          marketplace_total?: number | null
          planned_stockout_date?: string | null
          potential_revenue_per_unit?: number | null
          potential_revenue_total?: number | null
          recommended_supply_qty?: number | null
          snapshot_date: string
          source_row_hash?: string | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Update: {
          at_photo_studio?: number | null
          availability_days?: number | null
          availability_indicator?: string | null
          created_at?: string
          defective?: number | null
          fbs_stock?: number | null
          id?: string
          in_sale?: number | null
          in_supply?: number | null
          in_transit_from_client?: number | null
          in_transit_to_client?: number | null
          is_running_out?: boolean | null
          long_term_storage?: number | null
          marketplace_total?: number | null
          planned_stockout_date?: string | null
          potential_revenue_per_unit?: number | null
          potential_revenue_total?: number | null
          recommended_supply_qty?: number | null
          snapshot_date?: string
          source_row_hash?: string | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "inventory_snapshots_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "report_uploads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "inventory_snapshots_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "product_variants"
            referencedColumns: ["id"]
          },
        ]
      }
      product_ad_mappings: {
        Row: {
          ad_id: string
          created_at: string
          id: string
          product_id: string | null
          updated_at: string
        }
        Insert: {
          ad_id: string
          created_at?: string
          id?: string
          product_id?: string | null
          updated_at?: string
        }
        Update: {
          ad_id?: string
          created_at?: string
          id?: string
          product_id?: string | null
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "product_ad_mappings_product_id_fkey"
            columns: ["product_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
        ]
      }
      product_comments: {
        Row: {
          comment_date: string
          content: string
          created_at: string
          id: string
          product_id: string | null
          updated_at: string
          user_id: string | null
          variant_id: string | null
        }
        Insert: {
          comment_date: string
          content: string
          created_at?: string
          id?: string
          product_id?: string | null
          updated_at?: string
          user_id?: string | null
          variant_id?: string | null
        }
        Update: {
          comment_date?: string
          content?: string
          created_at?: string
          id?: string
          product_id?: string | null
          updated_at?: string
          user_id?: string | null
          variant_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "product_comments_product_id_fkey"
            columns: ["product_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "product_comments_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "product_variants"
            referencedColumns: ["id"]
          },
        ]
      }
      product_variants: {
        Row: {
          barcode: string
          cost_price: number | null
          created_at: string
          dimension_group: string | null
          id: string
          product_id: string
          sku: string
          updated_at: string
        }
        Insert: {
          barcode: string
          cost_price?: number | null
          created_at?: string
          dimension_group?: string | null
          id?: string
          product_id: string
          sku: string
          updated_at?: string
        }
        Update: {
          barcode?: string
          cost_price?: number | null
          created_at?: string
          dimension_group?: string | null
          id?: string
          product_id?: string
          sku?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "product_variants_product_id_fkey"
            columns: ["product_id"]
            isOneToOne: false
            referencedRelation: "products"
            referencedColumns: ["id"]
          },
        ]
      }
      products: {
        Row: {
          category: string | null
          created_at: string
          id: string
          name: string
          shop_id: string | null
          updated_at: string
          uzum_product_id: string
        }
        Insert: {
          category?: string | null
          created_at?: string
          id?: string
          name: string
          shop_id?: string | null
          updated_at?: string
          uzum_product_id: string
        }
        Update: {
          category?: string | null
          created_at?: string
          id?: string
          name?: string
          shop_id?: string | null
          updated_at?: string
          uzum_product_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "products_shop_id_fkey"
            columns: ["shop_id"]
            isOneToOne: false
            referencedRelation: "shops"
            referencedColumns: ["id"]
          },
        ]
      }
      profiles: {
        Row: {
          avatar_url: string | null
          created_at: string
          full_name: string | null
          id: string
          phone: string | null
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          full_name?: string | null
          id: string
          phone?: string | null
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          full_name?: string | null
          id?: string
          phone?: string | null
          updated_at?: string
        }
        Relationships: []
      }
      report_uploads: {
        Row: {
          created_at: string
          error_message: string | null
          file_name: string | null
          id: string
          report_date_from: string | null
          report_date_to: string | null
          report_type: string
          rows_imported: number | null
          status: string | null
          user_id: string | null
        }
        Insert: {
          created_at?: string
          error_message?: string | null
          file_name?: string | null
          id?: string
          report_date_from?: string | null
          report_date_to?: string | null
          report_type: string
          rows_imported?: number | null
          status?: string | null
          user_id?: string | null
        }
        Update: {
          created_at?: string
          error_message?: string | null
          file_name?: string | null
          id?: string
          report_date_from?: string | null
          report_date_to?: string | null
          report_type?: string
          rows_imported?: number | null
          status?: string | null
          user_id?: string | null
        }
        Relationships: []
      }
      sales: {
        Row: {
          cost_price: number | null
          created_at: string
          created_date: string | null
          id: string
          logistics_fee: number | null
          marketplace_commission: number | null
          order_number: string | null
          price: number | null
          promo_discount: number | null
          quantity: number
          received_date: string | null
          returns: number
          revenue: number | null
          revenue_net: number | null
          source_row_hash: string | null
          status: string | null
          upload_id: string | null
          variant_id: string | null
        }
        Insert: {
          cost_price?: number | null
          created_at?: string
          created_date?: string | null
          id?: string
          logistics_fee?: number | null
          marketplace_commission?: number | null
          order_number?: string | null
          price?: number | null
          promo_discount?: number | null
          quantity?: number
          received_date?: string | null
          returns?: number
          revenue?: number | null
          revenue_net?: number | null
          source_row_hash?: string | null
          status?: string | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Update: {
          cost_price?: number | null
          created_at?: string
          created_date?: string | null
          id?: string
          logistics_fee?: number | null
          marketplace_commission?: number | null
          order_number?: string | null
          price?: number | null
          promo_discount?: number | null
          quantity?: number
          received_date?: string | null
          returns?: number
          revenue?: number | null
          revenue_net?: number | null
          source_row_hash?: string | null
          status?: string | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "sales_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "report_uploads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "sales_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "product_variants"
            referencedColumns: ["id"]
          },
        ]
      }
      shops: {
        Row: {
          created_at: string
          id: string
          name: string
          updated_at: string
          user_id: string | null
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          updated_at?: string
          user_id?: string | null
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          updated_at?: string
          user_id?: string | null
        }
        Relationships: []
      }
      storage_costs: {
        Row: {
          avg_daily_sales_15d: number | null
          avg_daily_stock_15d: number | null
          created_at: string
          daily_storage_cost_per_unit: number | null
          daily_storage_cost_total: number | null
          fbo_stock_total: number | null
          id: string
          monthly_storage_cost: number | null
          snapshot_date: string
          source_row_hash: string | null
          storage_type: string | null
          turnover_days: number | null
          upload_id: string | null
          variant_id: string | null
        }
        Insert: {
          avg_daily_sales_15d?: number | null
          avg_daily_stock_15d?: number | null
          created_at?: string
          daily_storage_cost_per_unit?: number | null
          daily_storage_cost_total?: number | null
          fbo_stock_total?: number | null
          id?: string
          monthly_storage_cost?: number | null
          snapshot_date: string
          source_row_hash?: string | null
          storage_type?: string | null
          turnover_days?: number | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Update: {
          avg_daily_sales_15d?: number | null
          avg_daily_stock_15d?: number | null
          created_at?: string
          daily_storage_cost_per_unit?: number | null
          daily_storage_cost_total?: number | null
          fbo_stock_total?: number | null
          id?: string
          monthly_storage_cost?: number | null
          snapshot_date?: string
          source_row_hash?: string | null
          storage_type?: string | null
          turnover_days?: number | null
          upload_id?: string | null
          variant_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "storage_costs_upload_id_fkey"
            columns: ["upload_id"]
            isOneToOne: false
            referencedRelation: "report_uploads"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "storage_costs_variant_id_fkey"
            columns: ["variant_id"]
            isOneToOne: false
            referencedRelation: "product_variants"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      user_owns_product: { Args: { product_uuid: string }; Returns: boolean }
      user_owns_shop: { Args: { shop_uuid: string }; Returns: boolean }
      user_owns_variant: { Args: { variant_uuid: string }; Returns: boolean }
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {},
  },
} as const
