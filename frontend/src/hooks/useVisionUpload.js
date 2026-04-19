import { useRef, useState } from 'react';

export function useVisionUpload() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const fileInputRef = useRef(null);

  function handleFileChange(f) {
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  function reset() {
    setFile(null);
    setPreview(null);
  }

  return { file, preview, fileInputRef, handleFileChange, reset };
}
