import { cp, mkdir, rm, copyFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve(process.cwd());
const source = resolve(root, 'app', 'static');
const output = resolve(root, 'vercel_dist');

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, resolve(output, 'static'), { recursive: true });
await copyFile(resolve(source, 'index.html'), resolve(output, 'index.html'));
await copyFile(resolve(source, 'assets', 'brand', 'coco-aid-favicon.png'), resolve(output, 'favicon.ico'));
console.log('COCOAID Vercel frontend built at vercel_dist/');
