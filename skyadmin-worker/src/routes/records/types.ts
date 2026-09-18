export interface IssuedLicenseRow {
  id: number;
  machine_id: string;
  license_key: string;
  passcode: string;
  package_days: number | null;
  expires_at: string | null;
  nonce: string;
  issued_at: string;
  price_thb: number;
  revoked: number;
  used: number;
}

export interface SummarySourceRow {
  machine_id: string;
  expires_at: string | null;
  issued_at: string;
  package_days: number | null;
  nonce: string;
  revoked: number | boolean;
  used: number | boolean;
}

export interface RecordsPage {
  page: number;
  limit: number;
  offset: number;
  summaryLimit: number;
}
