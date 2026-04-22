import { useEffect, useRef, useState } from 'react';

export function useVisionUpload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);
  const previewRef = useRef(null);

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  function handleFileChange(f) {
    if (previewRef.current) {
      URL.revokeObjectURL(previewRef.current);
    }
    const nextPreview = URL.createObjectURL(f);
    previewRef.current = nextPreview;
    setFile(f);
    setPreview(nextPreview);
  }

  function reset() {
    setFile(null);
    setPreview(null);
  }

  return { file, preview, fileInputRef, handleFileChange, reset };
}
