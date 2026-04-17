<template>
  <div class="min-h-screen bg-gradient-to-b from-slate-50 to-blue-50 text-slate-900">
    <header class="border-b border-slate-200 bg-white/70 backdrop-blur">
      <nav class="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <NuxtLink to="/" class="text-lg font-bold tracking-tight">Wohnort-Kompass</NuxtLink>
        <div class="flex gap-4 text-sm font-medium">
          <NuxtLink to="/finder">Finder</NuxtLink>
          <NuxtLink to="/results">Ranking</NuxtLink>
          <NuxtLink to="/compare">Compare</NuxtLink>
          <NuxtLink to="/methodik">Methodik</NuxtLink>
        </div>
      </nav>
    </header>
    <main class="mx-auto max-w-6xl px-4 py-8">
      <NuxtPage />
    </main>
  </div>
</template>
