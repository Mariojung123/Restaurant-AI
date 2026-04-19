import { post, postFile } from './client';

export function previewInvoice(file) {
  return postFile('/api/vision/invoice/preview', file);
}

export function confirmInvoice(payload) {
  return post('/api/vision/invoice/confirm', payload);
}

export function previewReceipt(file) {
  return postFile('/api/vision/receipt/preview', file);
}

export function confirmReceipt(payload) {
  return post('/api/vision/receipt/confirm', payload);
}
