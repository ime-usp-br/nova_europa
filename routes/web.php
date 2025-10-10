<?php

use Illuminate\Support\Facades\Route;
use Livewire\Volt\Volt;

Route::view('/', 'welcome')
    ->middleware(['auth', 'verified'])
    ->name('welcome');

Route::view('dashboard', 'dashboard')
    ->middleware(['auth', 'verified'])
    ->name('dashboard');

Route::view('profile', 'profile')
    ->middleware(['auth'])
    ->name('profile');

Volt::route('evolucao', 'pages.evolucao')
    ->middleware(['auth', 'verified'])
    ->name('evolucao');

require __DIR__.'/auth.php';
