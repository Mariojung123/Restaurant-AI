import { ImageUploadZone } from '../ImageUploadZone.jsx';

export function VisionUploadStep({ title, icon, hint, preview, fileInputRef, onFile, file, loading, error, onAnalyze }) {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <ImageUploadZone
        preview={preview}
        fileInputRef={fileInputRef}
        onFile={onFile}
        icon={icon}
        hint={hint}
      />
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <button
        onClick={onAnalyze}
        disabled={!file || loading}
        className="bg-brand text-white px-4 py-2 rounded-lg font-medium disabled:opacity-40"
      >
        {loading ? 'Analyzing...' : 'Analyze'}
      </button>
    </div>
  );
}
