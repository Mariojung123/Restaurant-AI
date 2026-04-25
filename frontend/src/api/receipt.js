import { get } from './client.js';

export const fetchReceiptHistory = () => get('/api/vision/receipt/history');
