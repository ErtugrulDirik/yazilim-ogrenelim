import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		schema: docsSchema({
			// Dersin, fazın gereksinimlerine ek olarak istedikleri (src/gereksinimler.mjs).
			extend: z.object({
				gereksinimler: z.array(z.string()).optional(),
				gereksinimNotu: z.string().optional(),
				windowsNotu: z.string().optional(),
			}),
		}),
	}),
};
