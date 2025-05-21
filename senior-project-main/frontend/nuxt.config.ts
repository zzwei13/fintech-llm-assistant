import { defineNuxtConfig } from 'nuxt/config';

export default defineNuxtConfig({
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:3001', // 後端 API 的基本 URL
    },
  },

  compatibilityDate: '2024-07-21',
});