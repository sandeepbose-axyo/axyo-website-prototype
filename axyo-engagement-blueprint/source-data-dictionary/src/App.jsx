import React, { useState, useMemo, useRef } from 'react';

// --- Raw Data Processing ---
const rawCsvData = `
collection,field,type
sales_orders,order_id,string
sales_orders,order_date,date
sales_orders,sku_id,string
sales_orders,customer_id,string
sales_orders,region,string
sales_orders,quantity,int
sales_orders,net_amount,float
sales_orders,currency,string
product_master,sku_id,string
product_master,product_name,string
product_master,category,string
product_master,subcategory,string
product_master,unit_price,float
product_master,unit_cost,float
promotions,promo_id,string
promotions,sku_id,string
promotions,start_date,date
promotions,end_date,date
promotions,discount_pct,float
promotions,promo_type,string
inventory_levels,snapshot_date,date
inventory_levels,sku_id,string
inventory_levels,warehouse_id,string
inventory_levels,quantity_on_hand,int
inventory_levels,safety_stock,int
customer_master,customer_id,string
customer_master,customer_name,string
customer_master,channel,string
customer_master,tier,string
supplier_data,supplier_id,string
supplier_data,material_name,string
supplier_data,lead_time_days,int
exchange_rates,date,date
exchange_rates,from_currency,string
exchange_rates,to_currency,string
exchange_rates,rate,float
economic_indicators,date,date
economic_indicators,indicator_name,string
economic_indicators,value,float
commodity_prices,date,date
commodity_prices,commodity,string
commodity_prices,price,float
`;

const processData = () => {
    const totalCollections = 9;
    const totalAttributes = 41;

    const topCollections = [
        { name: 'sales_orders', count: 8 },
        { name: 'product_master', count: 6 },
        { name: 'promotions', count: 6 },
        { name: 'inventory_levels', count: 5 },
        { name: 'customer_master', count: 4 },
        { name: 'supplier_data', count: 3 },
        { name: 'commodity_prices', count: 3 },
        { name: 'economic_indicators', count: 3 },
        { name: 'exchange_rates', count: 3 },
    ];
    
    const rows = rawCsvData.trim().split('\n').slice(1);
    const data = rows.map(row => {
        const [collection, field, type] = row.split(',');
        return { collection, field, type };
    });

    const collections = {};
    data.forEach(item => {
        if (!collections[item.collection]) {
            collections[item.collection] = [];
        }
        collections[item.collection].push(item);
    });

    return { collections, totalCollections, totalAttributes, topCollections };
};

const { collections: allData, totalCollections, totalAttributes, topCollections } = processData();

const getFieldMetadata = (collection, field) => {
    const c = collection ? collection.toLowerCase() : '';
    const f = field ? field.toLowerCase() : '';

    let metadata = {
        description: "A standard operational field for this collection.",
        purpose: "Stores application data related to the collection's function.",
        constraints: "Follows standard data type validation."
    };

    if (f.endsWith('_id') && !f.includes('.')) {
        const entity = f.replace(/_id$/, '');
        metadata = {
            description: `A unique identifier (foreign key) linking this record to a document in the '${entity}_master' or related collection.`,
            purpose: `Establishes a relationship between '${c}' and '${entity}', enabling data joins and lookups.`,
            constraints: "Must correspond to a valid, existing document in the target collection."
        };
    }
    
    const specificMetadata = {
        sales_orders: {
            order_date: { description: "Timestamp when the customer order was placed.", purpose: "The primary time-series index for all sales forecasting models." },
            net_amount: { description: "The final financial value of the order line after discounts.", purpose: "The primary target variable for revenue forecasting models." },
            quantity: { description: "The number of units of a specific SKU sold in the transaction.", purpose: "The primary target variable for demand/unit forecasting models." },
        },
        product_master: {
            category: { description: "The high-level product category (e.g., 'Circuit Breakers', 'Transformers').", purpose: "Used for hierarchical aggregation and analysis of sales trends." },
            unit_cost: { description: "The cost of goods sold (COGS) for a single unit.", purpose: "Essential for calculating profit margins and running profitability scenarios." },
        },
        inventory_levels: {
            quantity_on_hand: { description: "The number of units available in a specific warehouse on a given date.", purpose: "Critical for calculating inventory turnover, identifying excess stock, and preventing stock-outs." },
            safety_stock: { description: "The minimum level of inventory to be maintained.", purpose: "A key input for inventory optimization models." },
        },
        customer_master: {
            channel: { description: "The sales channel through which the customer purchases (e.g., 'Direct', 'Distributor', 'Web').", purpose: "Allows for channel-specific forecasting and performance analysis." },
        },
        commodity_prices: {
            commodity: { description: "The name of the raw material (e.g., 'Copper', 'Aluminum').", purpose: "Links price data to specific materials." },
            price: { description: "The market price for the commodity on a given date.", purpose: "**Crucial external signal.** Used to model the impact of raw material cost volatility on product cost and sales demand." },
        },
        economic_indicators: {
            indicator_name: { description: "The name of the macroeconomic indicator (e.g., 'PMI', 'Housing Starts').", purpose: "Links values to specific economic trends." },
            value: { description: "The value of the indicator on a given date.", purpose: "**Crucial external signal.** Used to correlate broader economic health with product demand." },
        }
    };
    
    if (specificMetadata[c] && specificMetadata[c][f]) {
        return { ...metadata, ...specificMetadata[c][f] };
    }

    return metadata;
};

const topCollectionDescriptions = {
    sales_orders: {
        description: "The transactional heart of the dataset, recording every individual sale.",
        purpose: "To provide the foundational historical data for all demand and revenue forecasting. It's the primary source for the model's target variable (net_amount or quantity).",
        attributes: ["order_date", "sku_id", "quantity", "net_amount", "region"]
    },
    product_master: {
        description: "The definitive catalog of all products, containing descriptive attributes and pricing information.",
        purpose: "To enrich sales data with product-specific details like category and cost, enabling hierarchical aggregation and margin analysis.",
        attributes: ["sku_id", "category", "unit_price", "unit_cost"]
    },
    promotions: {
        description: "Contains details of all marketing promotions, including timing, duration, and discount levels.",
        purpose: "To allow the AI model to learn the impact of promotional activities on sales lift and cannibalization, a key driver of forecast variance.",
        attributes: ["promo_id", "sku_id", "start_date", "end_date", "discount_pct"]
    },
    inventory_levels: {
        description: "A snapshot of inventory quantities at various locations over time.",
        purpose: "To correlate sales with on-hand inventory, identify potential stock-out situations that suppressed historical sales, and measure the outcome of improved forecasts.",
        attributes: ["snapshot_date", "sku_id", "warehouse_id", "quantity_on_hand"]
    },
    customer_master: {
        description: "The master list of all customers and their attributes.",
        purpose: "To segment sales data by customer type and channel, enabling more granular and accurate forecasts.",
        attributes: ["customer_id", "customer_name", "channel", "tier"]
    },
    supplier_data: {
        description: "Contains information on suppliers and the lead times for key materials.",
        purpose: "To inform the 'what-if' analysis module about supply-side constraints and model the impact of lead time variability.",
        attributes: ["supplier_id", "material_name", "lead_time_days"]
    },
    commodity_prices: {
        description: "Time-series data of market prices for critical raw materials like copper.",
        purpose: "To provide a powerful external signal to the AI model, allowing it to predict the lagged impact of commodity price changes on costs and demand.",
        attributes: ["date", "commodity", "price"]
    },
    economic_indicators: {
        description: "Time-series data for key macroeconomic indicators like the Purchasing Managers' Index (PMI).",
        purpose: "To provide the model with context about the broader economic environment, improving its ability to forecast demand during economic shifts.",
        attributes: ["date", "indicator_name", "value"]
    },
    exchange_rates: {
        description: "Historical exchange rates between different currencies.",
        purpose: "To normalize financial data from different regions into a single currency for accurate global forecasting.",
        attributes: ["date", "from_currency", "to_currency", "rate"]
    }
};

// --- Components ---

const Tab = ({ label, isActive, onClick }) => (
    <button
      onClick={onClick}
      className={`px-4 sm:px-6 py-3 text-sm font-bold transition-colors duration-200 focus:outline-none ${
        isActive
          ? 'border-b-2 border-blue-600 text-blue-600'
          : 'border-b-2 border-transparent text-gray-500 hover:text-gray-700'
      }`}
    >
      {label}
    </button>
);

const Header = () => (
    <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-gray-800">Source Data Dictionary</h1>
        <p className="text-lg text-gray-500 mt-2">Use Case: Predictive Sales & Demand Intelligence</p>
    </header>
);

const OverviewTab = ({ onCollectionClick }) => (
    <div className="space-y-8">
        <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold text-gray-700 mb-3">Dataset Description</h2>
            <p className="text-gray-600 leading-relaxed">
                This dataset represents the core operational data for a global electrical manufacturer. It provides a comprehensive view of the entire commercial lifecycle, from product definition to final sale. The data is structured around key entities such as **Products**, **Customers**, and **Sales Orders**. 
                <br /><br />
                Crucially, the dataset includes not only internal transactional records but also external time-series data for **Commodity Prices** (e.g., copper) and **Economic Indicators** (e.g., PMI). This fusion of internal and external data is the key to building a resilient, forward-looking AI model that can move beyond simple historical extrapolation to understand and predict the impact of real-world market dynamics on the business.
            </p>
        </div>
        <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Metadata Summary</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
                <div className="bg-blue-50 p-4 rounded-lg">
                    <p className="text-4xl font-bold text-blue-600">{totalCollections}</p>
                    <p className="text-sm text-blue-800">Total Collections</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                    <p className="text-4xl font-bold text-green-600">{totalAttributes}</p>
                    <p className="text-sm text-green-800">Total Attributes</p>
                </div>
                <div className="bg-indigo-50 p-4 rounded-lg">
                    <p className="text-4xl font-bold text-indigo-600">{(totalAttributes / totalCollections).toFixed(1)}</p>
                    <p className="text-sm text-indigo-800">Avg. Attributes per Collection</p>
                </div>
            </div>
            <div className="mt-8">
                 <h2 className="text-2xl font-semibold text-gray-700 mb-4">Key Collection Descriptions</h2>
                 <div className="space-y-4">
                    {topCollections.map(({ name, count }) => {
                        const details = topCollectionDescriptions[name] || {};
                        return (
                            <div key={name} className="bg-gray-50 p-4 rounded-lg border">
                                <div className="flex justify-between items-start">
                                    <h3 className="text-lg font-bold text-blue-700">{name}</h3>
                                     <span className="text-sm font-bold text-gray-500 bg-gray-200 px-2 py-1 rounded-full">{count} attributes</span>
                                </div>
                                <p className="text-sm text-gray-600 mt-2"><strong>Description:</strong> {details.description}</p>
                                <p className="text-sm text-gray-600 mt-1"><strong>Purpose:</strong> {details.purpose}</p>
                                <p className="text-sm text-gray-600 mt-2"><strong>Illustrative Attributes:</strong> <code className="text-xs bg-gray-200 p-1 rounded">{details.attributes?.join(', ')}</code></p>
                                <button onClick={() => onCollectionClick(name)} className="text-sm text-blue-600 hover:underline mt-2">View all attributes &rarr;</button>
                            </div>
                        )
                    })}
                 </div>
            </div>
        </div>
    </div>
);

const InsightsTab = () => (
    <div className="bg-white p-6 rounded-lg shadow-md space-y-8">
        <div>
            <h2 className="text-2xl font-semibold text-gray-700 mb-3">Deeper Insights for EDA</h2>
            <div className="space-y-6 text-gray-600 leading-relaxed">
                <div>
                    <h3 className="text-lg font-semibold text-gray-800">1. The Core Relational Hub: Sales, Products, and Customers</h3>
                    <p>The entire dataset is anchored by the **`sales_orders`** collection. Every record links to a `sku_id` in **`product_master`** and a `customer_id` in **`customer_master`**. This classic star schema is ideal for analysis, allowing for easy joins to slice and dice sales data by product attributes (like `category`) or customer attributes (like `channel`).</p>
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-gray-800">2. The Time-Series Backbone</h3>
                    <p>The presence of a `date` or `timestamp` field in nearly every collection (**`sales_orders`**, **`inventory_levels`**, **`promotions`**, **`commodity_prices`**, etc.) is critical. This confirms the dataset is well-suited for time-series forecasting. The most important relationship will be aligning the **`sales_orders.order_date`** with the corresponding dates in the external data collections.</p>
                </div>
                 <div>
                    <h3 className="text-lg font-semibold text-gray-800">3. Fusing Internal Levers with External Forces</h3>
                    <p>This dataset's primary strength is its potential for a driver-based forecast. The model can learn not just from internal actions recorded in **`promotions`** but also from external market dynamics in **`commodity_prices`** and **`economic_indicators`**. The ability to correlate a spike in the `copper_index` with sales of specific product categories six weeks later is the key to moving from reactive to predictive planning.</p>
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-gray-800">4. Inventory as Both an Input and an Outcome</h3>
                    <p>The **`inventory_levels`** collection is unique. It can serve as an input to the model (a stock-out in the past may have suppressed sales, which the model needs to know) and as a key outcome metric (the goal of a better forecast is to optimize `quantity_on_hand`). This dual role is essential for building a comprehensive S&OP solution.</p>
                </div>
            </div>
        </div>
    </div>
);

const DataDictionaryTab = ({ collections, collectionRefs }) => {
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCollection, setSelectedCollection] = useState('All');

    const allCollectionNames = useMemo(() => Object.keys(collections).sort(), [collections]);

    const filteredCollections = useMemo(() => {
        let collectionsCopy = JSON.parse(JSON.stringify(collections));

        if (selectedCollection !== 'All') {
            const filtered = {};
            if (collectionsCopy[selectedCollection]) {
                 filtered[selectedCollection] = collectionsCopy[selectedCollection];
            }
            collectionsCopy = filtered;
        }

        if (searchTerm) {
            Object.keys(collectionsCopy).forEach(collectionName => {
                const filteredFields = collectionsCopy[collectionName].filter(attribute => 
                    attribute.field.toLowerCase().includes(searchTerm.toLowerCase())
                );
                if (filteredFields.length > 0) {
                    collectionsCopy[collectionName] = filteredFields;
                } else {
                    delete collectionsCopy[collectionName];
                }
            });
        }
        return collectionsCopy;
    }, [searchTerm, selectedCollection, collections]);

    const sortedCollectionNames = Object.keys(filteredCollections);

    return (
        <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4">Data Dictionary</h2>
            <div className="flex flex-col md:flex-row gap-4 mb-6 p-4 bg-gray-50 rounded-lg border sticky top-0 z-10">
                <input 
                    type="text"
                    placeholder="Search by field name..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="flex-grow p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                />
                <select
                    value={selectedCollection}
                    onChange={(e) => {
                        setSearchTerm('');
                        setSelectedCollection(e.target.value);
                    }}
                    className="p-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                >
                    <option value="All">All Collections</option>
                    {allCollectionNames.map(name => (
                        <option key={name} value={name}>{name}</option>
                    ))}
                </select>
            </div>
            {sortedCollectionNames.length > 0 ? sortedCollectionNames.map(name => (
                 <div key={name} ref={el => collectionRefs.current[name] = el}>
                    <AttributeTable collectionName={name} attributes={filteredCollections[name]} />
                 </div>
            )) : <p className="text-gray-500">No matching collections or fields found.</p>}
        </div>
    );
};

const AttributeTable = ({ collectionName, attributes }) => (
    <div className="mb-10">
        <h3 className="text-2xl font-semibold text-gray-800 mb-4 pb-2 border-b-2 border-blue-500">{collectionName}</h3>
        <div className="overflow-x-auto">
            <table className="min-w-full bg-white border">
                <thead className="bg-gray-100">
                    <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/5">Field Name</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-2/5">Business Description & Purpose</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/5">Data Type</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/5">Potential Constraints</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                    {attributes.map(({ field, type }) => {
                        const metadata = getFieldMetadata(collectionName, field);
                        return (
                            <tr key={field} className="hover:bg-gray-50">
                                <td className="px-4 py-3 text-sm font-mono text-gray-900 break-all">{field}</td>
                                <td className="px-4 py-3 text-sm text-gray-600">
                                    <p className="font-semibold">{metadata.description}</p>
                                    <p className="text-xs text-gray-500 mt-1"><strong>Purpose:</strong> {metadata.purpose}</p>
                                </td>
                                <td className="px-4 py-3 text-sm font-mono text-gray-700">{type}</td>
                                <td className="px-4 py-3 text-sm text-gray-600">{metadata.constraints}</td>
                            </tr>
                        );
                    })}
                </tbody>
            </table>
        </div>
    </div>
);


export default function App() {
    const [activeTab, setActiveTab] = useState('Overview');
    const collectionRefs = useRef({});

    const handleCollectionClick = (collectionName) => {
        setActiveTab('Data Dictionary');
        setTimeout(() => {
            if (collectionRefs.current[collectionName]) {
                collectionRefs.current[collectionName].scrollIntoView({
                    behavior: 'smooth',
                    block: 'start',
                });
            }
        }, 100);
    };

    const tabs = ['Overview', 'Deeper Insights', 'Data Dictionary'];

    return (
        <div className="bg-gray-50 min-h-screen font-sans p-4 sm:p-8">
            <div className="max-w-7xl mx-auto">
                <Header />
                <nav className="bg-white rounded-t-lg shadow-md">
                    <div className="flex border-b border-gray-200">
                        {tabs.map(tab => (
                            <Tab 
                                key={tab} 
                                label={tab} 
                                isActive={activeTab === tab} 
                                onClick={() => setActiveTab(tab)} 
                            />
                        ))}
                    </div>
                </nav>
                <div className="py-6">
                    {activeTab === 'Overview' && <OverviewTab onCollectionClick={handleCollectionClick} />}
                    {activeTab === 'Deeper Insights' && <InsightsTab />}
                    {activeTab === 'Data Dictionary' && <DataDictionaryTab collections={allData} collectionRefs={collectionRefs} />}
                </div>
                 <footer className="text-center mt-12 text-xs text-gray-400">
                    <p>Source Data Dictionary | Powered by Axyo</p>
                </footer>
            </div>
        </div>
    );
}

