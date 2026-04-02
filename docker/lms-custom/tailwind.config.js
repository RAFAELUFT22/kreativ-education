import frappeUIPreset from 'frappe-ui/tailwind'

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		extend: {
			strokeWidth: {
				1.5: '1.5',
			},
			screens: {
				'2xl': '1600px',
				'3xl': '1920px',
			},
			colors: {
				'tds-primary':  '#003CDC',
				'tds-navy':     '#003366',
				'tds-teal':     '#008080',
				'tds-yellow':   '#F9C300',
				'tds-green':    '#14B414',
				'tds-red':      '#F02814',
				'tds-bg':       '#F4F7F6',
			},
			fontFamily: {
				sans:     ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
				heading:  ['Montserrat', 'ui-sans-serif', 'sans-serif'],
			},
			backgroundImage: {
				'tds-hero':        'linear-gradient(135deg, #003366 0%, #003CDC 60%, #008080 100%)',
				'tds-card':        'linear-gradient(to top right, #003366, #003CDC)',
				'tds-yellow-card': 'linear-gradient(to top right, #cc9f00, #F9C300)',
				'tds-green-card':  'linear-gradient(to top right, #0a6b0a, #14B414)',
			},
			boxShadow: {
				'tds':    '0 4px 16px rgba(0, 60, 220, 0.12)',
				'tds-lg': '0 8px 32px rgba(0, 60, 220, 0.16)',
			},
		},
	},
	plugins: [],
}
