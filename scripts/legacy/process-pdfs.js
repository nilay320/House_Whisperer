import { PDFLoader } from 'langchain/document_loaders/fs/pdf';
import { RecursiveCharacterTextSplitter } from 'langchain/text_splitter';
import fs from 'fs';
import path from 'path';

const PDF_DIRS = [
  '../docs/data/SOP/',
  '../docs/data/ North Carolina Building & Inspection Codes /'
];

async function loadPDFs() {
  const documents = [];
  
  for (const dir of PDF_DIRS) {
    const fullPath = path.join(process.cwd(), dir);
    if (!fs.existsSync(fullPath)) {
      console.log(`Directory not found: ${fullPath}`);
      continue;
    }
    
    const files = fs.readdirSync(fullPath);
    const pdfFiles = files.filter(file => file.endsWith('.pdf'));
    
    for (const pdfFile of pdfFiles) {
      const filePath = path.join(fullPath, pdfFile);
      console.log(`Processing: ${pdfFile}`);
      
      try {
        const loader = new PDFLoader(filePath);
        const docs = await loader.load();
        
        // Add metadata
        docs.forEach(doc => {
          doc.metadata.source = pdfFile;
          doc.metadata.section = dir.includes('SOP') ? 'Standards of Practice' : 'Building Codes';
        });
        
        documents.push(...docs);
      } catch (error) {
        console.error(`Error processing ${pdfFile}:`, error);
      }
    }
  }
  
  return documents;
}

async function processAndIngest() {
  console.log('Loading PDFs...');
  const rawDocs = await loadPDFs();
  console.log(`Loaded ${rawDocs.length} pages from PDFs`);
  
  // Split documents into chunks
  const splitter = new RecursiveCharacterTextSplitter({
    chunkSize: 1500,
    chunkOverlap: 300,
    separators: ['\n\n', '\n', '.', '!', '?', ';', ':', ' ', ''],
  });
  
  const processedDocs = [];
  for (const doc of rawDocs) {
    const chunks = await splitter.splitText(doc.pageContent);
    chunks.forEach((chunk, index) => {
      processedDocs.push({
        content: chunk,
        source: doc.metadata.source,
        section: doc.metadata.section,
        page: doc.metadata.loc?.pageNumber || 'Unknown',
        chunkIndex: index
      });
    });
  }
  
  console.log(`Split into ${processedDocs.length} chunks`);
  
  // Send to ingestion endpoint
  const BATCH_SIZE = 50;
  for (let i = 0; i < processedDocs.length; i += BATCH_SIZE) {
    const batch = processedDocs.slice(i, i + BATCH_SIZE);
    console.log(`Ingesting batch ${Math.floor(i/BATCH_SIZE) + 1} of ${Math.ceil(processedDocs.length/BATCH_SIZE)}`);
    
    try {
      const response = await fetch('http://localhost:3000/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          documents: batch,
          reset: i === 0 // Only reset on first batch
        }),
      });
      
      const result = await response.json();
      console.log(`Batch result:`, result);
    } catch (error) {
      console.error(`Failed to ingest batch:`, error);
    }
  }
  
  console.log('Ingestion complete!');
}

// Run the processing
processAndIngest().catch(console.error);