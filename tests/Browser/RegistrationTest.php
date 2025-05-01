<?php

namespace Tests\Browser;

use Illuminate\Foundation\Testing\DatabaseMigrations;
use Laravel\Dusk\Browser;
use PHPUnit\Framework\Attributes\Group;
use PHPUnit\Framework\Attributes\Test;
use Tests\DuskTestCase;

class RegistrationTest extends DuskTestCase
{
    use DatabaseMigrations;

    /**
     * Verifica se o campo "Número USP (codpes)" é exibido condicionalmente
     * na tela de registro, com base no email ou no checkbox "Sou da USP",
     * e se o atributo 'required' é aplicado dinamicamente.
     */
    #[Test]
    #[Group('auth')]
    #[Group('dusk')]
    public function codpes_field_is_conditionally_displayed_and_required(): void
    {
        $this->browse(function (Browser $browser) {
            $browser->visit('/register')
                ->assertMissing('@codpes-container'); // AC4 - Initially hidden

            // Type non-USP email -> still hidden
            $browser->type('@email-input', 'test@example.com')
                // ->click('body') // Removed - click() might not be reliable here
                ->pause(150) // Increased pause slightly
                ->assertMissing('@codpes-container');

            // Check "Sou da USP" checkbox -> should appear and be required
            $browser->check('@is-usp-user-checkbox')
                ->pause(150) // Increased pause slightly
                ->waitFor('@codpes-container') // Use waitFor for visibility change
                ->assertVisible('@codpes-container') // AC6
                ->assertAttribute('@codpes-input', 'required', 'true'); // AC8

            // Uncheck "Sou da USP" checkbox -> should hide and not be required
            $browser->uncheck('@is-usp-user-checkbox')
                // ->click('body') // Removed
                ->pause(150) // Increased pause slightly
                ->waitUntilMissing('@codpes-container') // Use waitUntilMissing
                ->assertMissing('@codpes-container') // AC7
                ->assertAttributeMissing('@codpes-input', 'required'); // AC8 - Check attribute is missing

            // Clear email and type USP email -> should appear and be required
            $browser->clear('@email-input')
                ->type('@email-input', 'test@usp.br')
                // ->click('body') // Removed
                ->pause(150) // Increased pause slightly
                ->waitFor('@codpes-container')
                ->assertVisible('@codpes-container') // AC5
                ->assertAttribute('@codpes-input', 'required', 'true'); // AC8

            // Clear email and type non-USP email again -> should hide and not be required
            $browser->clear('@email-input')
                ->type('@email-input', 'another@example.com')
                ->uncheck('@is-usp-user-checkbox')
                ->pause(150) // Increased pause slightly
                ->waitUntilMissing('@codpes-container') // Wait for element to disappear
                ->assertMissing('@codpes-container') // AC7
                ->assertAttributeMissing('@codpes-input', 'required'); // AC8 - Check attribute is missing
        });
    }
}
