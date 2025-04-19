<?php

/**
 * Este arquivo contém uma implementação "Fake" para o SenhaUnica Socialite provider.
 * Permite simular respostas do servidor OAuth da Senha Única durante os testes
 * de feature, evitando chamadas HTTP reais.
 *
 * Coloque este arquivo em: tests/Fakes/FakeSenhaunicaSocialiteProvider.php
 */

namespace Tests\Fakes;

use Laravel\Socialite\Contracts\Provider as SocialiteProviderContract;
use Laravel\Socialite\Two\User as SocialiteUser; // Usado para mapeamento padrão

class FakeSenhaunicaSocialiteProvider implements SocialiteProviderContract
{
    protected array $userData;
    protected string $redirectUrl = 'https://fake.sso.usp.br/oauth/authorize?fake_params';

    /**
     * Cria uma nova instância do provider fake.
     *
     * @param array $userData Os dados do usuário fake a serem retornados.
     *                        Deve incluir chaves como 'codpes', 'nompes', 'email', 'vinculo'.
     */
    public function __construct(array $userData = [])
    {
        // Define dados padrão se nenhum for fornecido
        $this->userData = $userData ?: [
            'codpes' => '1234567',
            'nompes' => 'Usuário Fake Teste',
            'email' => 'fake.test@usp.br',
            'emailUsp' => 'fake.test@usp.br',
            'emailAlternativo' => null,
            'telefone' => null,
            'vinculo' => [
                [
                    'tipoVinculo' => 'SERVIDOR',
                    'codigoSetor' => 0,
                    'nomeAbreviadoSetor' => 'TESTE',
                    'nomeSetor' => 'Setor de Teste',
                    'codigoUnidade' => '99',
                    'siglaUnidade' => 'TEST',
                    'nomeUnidade' => 'Unidade de Teste',
                    'nomeAbreviadoFuncao' => 'Cargo Fake',
                    'tipoFuncao' => 'Servidor', // Essencial para HasSenhaunica Trait
                ],
            ],
        ];
    }

    /**
     * Simula o retorno dos dados do usuário.
     */
    public function user(): \Laravel\Socialite\Contracts\User
    {
        $user = new SocialiteUser();
        $user->map([
            'id' => $this->userData['codpes'] ?? null,
            'nickname' => $this->userData['nompes'] ?? null,
            'name' => $this->userData['nompes'] ?? null,
            'email' => $this->userData['email'] ?? ($this->userData['emailUsp'] ?? ($this->userData['emailAlternativo'] ?? null)),
            'avatar' => null, // SenhaUnica não fornece avatar
        ]);

        // Adiciona os dados específicos do SenhaUnica que o trait HasSenhaunica espera
        foreach ($this->userData as $key => $value) {
            if (! property_exists($user, $key)) {
                // Usar ->user para acessar o array interno do Socialite User
                $user->user[$key] = $value;
                // Adiciona também como propriedade mágica para acesso direto se necessário
                $user->{$key} = $value;
            }
        }

        // Adiciona um token fake (pode ser necessário para alguns fluxos)
        $user->token = 'fake-token-' . bin2hex(random_bytes(10));
        $user->tokenSecret = null; // OAuth1 não usa tokenSecret desta forma no callback final
        $user->refreshToken = null;
        $user->expiresIn = null;
        $user->approvedScopes = null; // Adicionado para compatibilidade com V5+

        return $user;
    }

    /**
     * Simula o redirecionamento para o provedor OAuth.
     */
    public function redirect()
    {
        return new \Illuminate\Http\RedirectResponse($this->redirectUrl);
    }

    /**
     * Define uma URL de redirecionamento para o teste.
     */
    public function setRedirectUrl(string $url): self
    {
        $this->redirectUrl = $url;
        return $this;
    }

    // --- Métodos da Interface Não Usados no Fluxo Básico ---
    // Implementações vazias ou que retornam $this para compatibilidade de tipo

    public function userFromToken($token)
    {
        // Implementação pode ser adicionada se o teste precisar deste método
        return $this->user();
    }

     public function userFromTokenAndSecret($token, $secret)
     {
        // Implementação pode ser adicionada se o teste precisar deste método
        return $this->user();
     }

    public function getAccessTokenResponse($code)
    {
        // Simular uma resposta de token se necessário
        return ['access_token' => 'fake-token', 'expires_in' => 3600];
    }

     public function getRefreshTokenResponse($refreshToken)
     {
         // Simular uma resposta de refresh token se necessário
         return ['access_token' => 'refreshed-fake-token', 'expires_in' => 3600];
     }

    public function scopes($scopes)
    {
        return $this;
    }

    public function setScopes($scopes)
    {
        return $this;
    }

     public function with($parameters)
     {
         return $this;
     }

     public function buildAuthUrlFromBase($url, $state)
     {
         return $url.'?state='.$state.'&fake_auth';
     }

     public function getCodeFields($state = null)
     {
        return ['code' => 'fake_code', 'state' => $state];
     }

    public function getState()
    {
        return 'fake_state';
    }

    public function userInstance()
    {
        return $this->user();
    }

    // Adicione outros métodos da interface se forem estritamente necessários
    // para os seus testes, mas geralmente `user()` e `redirect()` são suficientes
    // para mockar o fluxo de autenticação.
}