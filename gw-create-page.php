<?php
/**
 * Plugin Name: GW Create Page
 * Version: 1.0
 */
function gw_create_diseno_page() {
    if (!get_page_by_path('crear')) {
        wp_insert_post(array(
            'post_title' => 'Crear tu diseño',
            'post_name' => 'crear',
            'post_status' => 'publish',
            'post_type' => 'page',
            'post_content' => '<div style="width:100vw;height:100vh;margin:0;padding:0;overflow:hidden;position:absolute;top:0;left:0;z-index:9999;background:#0A0A0A"><iframe src="https://guanchewear-webhook.vercel.app/diseno" style="width:100%;height:100%;border:none;display:block" allow="payment *"></iframe></div>'
        ));
    }
}
add_action('init', 'gw_create_diseno_page');