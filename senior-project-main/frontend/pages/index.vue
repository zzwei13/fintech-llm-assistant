<template>
    <div>
      <h1>Users</h1>
      <ul>
        <li v-for="user in users" :key="user.id">{{ user.name }}</li>
      </ul>
    </div>
  </template>
  
  <script setup>
  import { useFetch, useRuntimeConfig } from '#app';
  
  const config = useRuntimeConfig();
  const { data, error } = await useFetch('/users', {
    baseURL: config.public.apiBase,
  });
  
  if (error.value) {
    console.error('Error fetching users:', error.value);
  }
  
  const users = data.value || [];
  </script>
  