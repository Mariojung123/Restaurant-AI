export function ImageUploadZone({ preview, fileInputRef, onFile, icon, hint }) {
  function handleDrop(e) {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) onFile(f);
  }

  return (
    <div
      className="border-2 border-dashed border-slate-300 rounded-lg p-10 flex flex-col items-center gap-3 cursor-pointer hover:border-brand transition-colors"
      onClick={() => fileInputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
    >
      {preview ? (
        <img src={preview} alt="preview" className="max-h-48 rounded" />
      ) : (
        <>
          <span className="text-4xl">{icon}</span>
          <p className="text-slate-500 text-sm">{hint}</p>
        </>
      )}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="hidden"
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />
    </div>
  );
}
