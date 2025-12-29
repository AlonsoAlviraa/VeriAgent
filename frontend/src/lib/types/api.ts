export enum InvoiceStatus {
    PENDING = "PENDING",
    VALIDATED = "VALIDATED",
    SIGNED = "SIGNED",
    SENT = "SENT",
    ERROR = "ERROR",
}

export interface Address {
    street: string;
    city: string;
    postal_code: string;
    country: string;
}

export interface Customer {
    tax_id: string;
    name: string;
    address: Address;
    email?: string;
}

export interface TaxLine {
    tax_type: string;
    tax_rate: number;
    base_amount: number;
    tax_amount: number;
}

export interface InvoiceLine {
    description: string;
    quantity: number;
    unit_price: number;
    total_amount: number;
}

export interface InvoiceInput {
    series: string;
    number: string;
    issue_date: string; // ISO format date string (YYYY-MM-DD)
    previous_invoice_hash?: string;
    issuer_tax_id: string;
    customer: Customer;
    lines: InvoiceLine[];
    taxes: TaxLine[];
    total_base: number;
    total_tax: number;
    total_amount: number;
}

export interface InvoiceValidatedData extends InvoiceInput {
    confidence_score: number;
}

export interface InvoiceOutput {
    id: string;
    series: string;
    number: string;
    status: InvoiceStatus;
    invoice_hash: string;
    previous_invoice_hash?: string;
    xml_preview?: string;
    message: string;
}

export interface SignRequest {
    invoice_id: string;
}

export interface SignResponse {
    invoice_id: string;
    signed: boolean;
    signature_hash?: string;
    error?: string;
}

export interface ErrorResponse {
    error_code: string;
    message: string;
    details?: Record<string, any>;
}

export interface UploadResponse {
    file_id: string;
    filename: string;
    content_type: string;
    size_bytes: number;
    status: string;
}
