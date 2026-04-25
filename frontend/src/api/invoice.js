import { get } from './client.js';

export const fetchInvoiceHistory = () => get('/api/vision/invoice/history');
